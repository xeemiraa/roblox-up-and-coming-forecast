#!/usr/bin/env python3
"""
Forecast Roblox Up-and-Coming chart top 10.
Read history from /input, output forecast to /output/forecast.json.
"""

import json
import os
import math
from collections import defaultdict
from pathlib import Path

INPUT_DIR = Path("/input")
OUTPUT_DIR = Path("/output")


def load_history():
    """Load chart history from /input/history.ndjson."""
    history = []
    history_file = INPUT_DIR / "history.ndjson"
    
    if not history_file.exists():
        print(f"Warning: {history_file} not found")
        return history
    
    with open(history_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    history.append(data)
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse line: {line[:50]}...")
    
    print(f"Loaded {len(history)} history entries")
    return history


def parse_chart_data(history):
    """Extract game data from history."""
    games = {}  # game_id -> {name, universe_id, ranks: [], player_counts: []}
    
    for entry in history:
        if not entry.get('ok'):
            continue
        
        chart = entry.get('up_and_coming', [])
        for game in chart:
            game_id = game.get('universe_id') or game.get('root_place_id')
            if not game_id:
                continue
            
            if game_id not in games:
                games[game_id] = {
                    'name': game.get('name'),
                    'universe_id': game_id,
                    'root_place_id': game.get('root_place_id'),
                    'ranks': [],
                    'player_counts': [],
                    'genres': set(),
                }
            
            games[game_id]['ranks'].append(game.get('rank', 0))
            games[game_id]['player_counts'].append(game.get('playing', 0) or 0)
            
            genre = game.get('genre')
            if genre:
                games[game_id]['genres'].add(genre)
    
    return games


def analyze_game_trends(games, history):
    """Analyze game trends to predict future positions."""
    game_scores = {}
    
    for game_id, data in games.items():
        ranks = data['ranks']
        players = data['player_counts']
        
        if len(ranks) < 2:
            continue
        
        # Calculate recent trend
        recent_ranks = ranks[-5:] if len(ranks) >= 5 else ranks
        recent_players = players[-5:] if len(players) >= 5 else players
        
        # Current rank (last)
        current_rank = ranks[-1]
        
        # Average rank over last few observations
        avg_rank = sum(recent_ranks) / len(recent_ranks)
        
        # Rank volatility (how much does it change?)
        if len(recent_ranks) > 1:
            rank_changes = [abs(recent_ranks[i] - recent_ranks[i-1]) for i in range(1, len(recent_ranks))]
            rank_volatility = sum(rank_changes) / len(rank_changes)
        else:
            rank_volatility = 0
        
        # Player count trend
        if len(recent_players) >= 2:
            player_growth = (recent_players[-1] - recent_players[0]) / (recent_players[0] + 1)
        else:
            player_growth = 0
        
        # Momentum (recent rank change)
        if len(ranks) >= 2:
            recent_change = ranks[-1] - ranks[-2]
        else:
            recent_change = 0
        
        # Calculate score (lower rank = better, higher player count = better)
        # Score = combination of current position, trend, momentum, volatility
        score = (
            -current_rank * 10  # Current rank is most important
            + player_growth * 5  # Player growth
            - rank_volatility * 2  # Lower volatility is better
            - abs(recent_change) * 1  # Consistent movement
        )
        
        game_scores[game_id] = {
            'score': score,
            'current_rank': current_rank,
            'avg_rank': avg_rank,
            'rank_volatility': rank_volatility,
            'player_growth': player_growth,
            'recent_change': recent_change,
            'name': data['name'],
            'player_count': players[-1] if players else 0,
            'ranks': ranks,
            'players': players,
        }
    
    return game_scores


def generate_forecast(game_scores, history):
    """Generate forecast for top 10 positions."""
    if not game_scores:
        return {
            'forecast': {
                'slots': [],
                'games': {}
            }
        }
    
    # Sort by score (higher is better)
    sorted_games = sorted(game_scores.items(), key=lambda x: x[1]['score'], reverse=True)
    
    # Top candidates for forecasting
    top_n = min(30, len(sorted_games))
    candidates = sorted_games[:top_n]
    
    # Calculate probabilities using softmax
    scores = [c[1]['score'] for c in candidates]
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    
    # Normalize scores to positive range
    if max_score > min_score:
        norm_scores = [(s - min_score + 0.1) for s in scores]
    else:
        norm_scores = [1.0] * len(scores)
    
    # Softmax
    exps = [math.exp(s / max(1, max(norm_scores))) for s in norm_scores]
    sum_exps = sum(exps)
    
    # Probability for each candidate
    candidate_probs = []
    for i, (game_id, data) in enumerate(candidates):
        prob = exps[i] / sum_exps if sum_exps > 0 else 1.0 / len(candidates)
        candidate_probs.append({
            'game_id': game_id,
            'name': data['name'],
            'prob': prob,
            'score': data['score'],
            'current_rank': data['current_rank'],
        })
    
    # Sort by probability
    candidate_probs.sort(key=lambda x: x['prob'], reverse=True)
    
    # Generate forecast for each of 72 hours
    # We'll create a forecast that covers the entire window
    forecast_start = "2026-11-13T06:00:00Z"
    forecast_end = "2026-11-16T06:00:00Z"
    
    # For each hour in the 72-hour window, predict top 10
    # Since we can't know exactly which hour, we'll create a forecast
    # that covers all hours with similar probabilities
    
    slots = []
    for place in range(1, 11):
        # For each place, assign probability to top candidates
        slot_games = []
        remaining_prob = 1.0
        
        for c in candidate_probs[:10]:  # Top 10 candidates
            prob = c['prob'] * 0.5  # Base probability
            if place <= len(candidate_probs):
                # Higher places get higher probabilities
                place_factor = 1.0 / place
                prob = c['prob'] * place_factor
            
            slot_games.append({
                'universe_id': c['game_id'],
                'name': c['name'],
                'probability': prob,
            })
            remaining_prob -= prob
        
        # Distribute remaining probability to "other" games
        if remaining_prob > 0:
            slot_games.append({
                'universe_id': 'other',
                'name': 'Other games',
                'probability': remaining_prob,
            })
        
        slots.append({
            'place': place,
            'games': slot_games,
        })
    
    # Build game list with all probabilities
    all_games = {}
    for c in candidate_probs:
        all_games[c['game_id']] = {
            'name': c['name'],
            'probabilities': {},
        }
        for place in range(1, 11):
            # Calculate probability for this game at this place
            if place <= len(candidate_probs):
                place_factor = 1.0 / place
                prob = c['prob'] * place_factor
            else:
                prob = 0.0
            all_games[c['game_id']]['probabilities'][str(place)] = prob
    
    return {
        'forecast': {
            'slots': slots,
            'games': all_games,
        },
        'metadata': {
            'forecast_start': forecast_start,
            'forecast_end': forecast_end,
            'num_hours': 72,
            'num_candidates': len(candidates),
        }
    }


def main():
    print("=" * 60)
    print("Roblox Up-and-Coming Forecast")
    print("=" * 60)
    
    # Load history
    history = load_history()
    
    if not history:
        print("No history data available")
        forecast = {
            'forecast': {
                'slots': [],
                'games': {}
            }
        }
    else:
        # Parse chart data
        games = parse_chart_data(history)
        print(f"Found {len(games)} unique games")
        
        # Analyze trends
        game_scores = analyze_game_trends(games, history)
        print(f"Analyzed {len(game_scores)} games")
        
        # Generate forecast
        forecast = generate_forecast(game_scores, history)
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Write forecast
    output_file = OUTPUT_DIR / "forecast.json"
    with open(output_file, 'w') as f:
        json.dump(forecast, f, indent=2)
    
    print(f"\nForecast written to {output_file}")
    print(f"Top 10 predictions:")
    for slot in forecast['forecast']['slots']:
        print(f"  Place {slot['place']}:")
        for game in slot['games'][:3]:
            print(f"    - {game['name']} (prob: {game['probability']:.4f})")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
