"""Baseline Kaggriculture agent.

This agent uses a simple wheat loop:
- buy wheat seeds when needed
- plant on empty unlocked tiles
- water planted wheat daily
- harvest wheat once it reaches first yield age
- sell any shed inventory each turn

The strategy is intentionally simple so it can be expanded later.
"""

CROP_DATA = {
    "WHEAT": {
        "first_yield_day": 2,
        "seed_cost": 10,
    },
}

SELLABLE_ITEMS = {
    "WHEAT",
    "CARROT",
    "TOMATO",
    "STRAWBERRY",
    "MELON",
    "EGG",
    "MILK",
    "WOOL",
    "FERTILIZER",
}


def in_bounds(x, y, width, height):
    return 0 <= x < width and 0 <= y < height


def move_towards(source, target):
    sx, sy = source
    tx, ty = target
    if sx < tx:
        return "EAST"
    if sx > tx:
        return "WEST"
    if sy < ty:
        return "SOUTH"
    if sy > ty:
        return "NORTH"
    return "PASS"


def find_nearest(start, positions):
    if not positions:
        return None
    sx, sy = start
    best = None
    best_dist = None
    for x, y in positions:
        dist = abs(sx - x) + abs(sy - y)
        if best is None or dist < best_dist:
            best = (x, y)
            best_dist = dist
    return best


def item_count(mapping, key):
    return mapping.get(key, 0)


def build_market_orders(obs, private):
    market = []
    # Sell everything in the shed that can be sold.
    for item, count in list(private.get("shed", {}).items()):
        if count and item in SELLABLE_ITEMS:
            market.append(["SELL", item, count])

    # Keep at least one wheat seed available.
    wheat_seeds = item_count(private.get("seeds", {}), "WHEAT")
    money = obs["farms"][obs["player"]]["money"]
    if wheat_seeds == 0 and money >= CROP_DATA["WHEAT"]["seed_cost"]:
        market.append(["BUY_SEED", "WHEAT", 1])
    return market


def step_marketable_actions(obs):
    player = obs["player"]
    me = obs["farms"][player]
    private = obs["private"]
    market = build_market_orders(obs, private)

    tiles = me["tiles"]
    height = len(tiles)
    width = len(tiles[0]) if height else 0
    farmer_x, farmer_y = me["farmer"]
    farmer_tile = tiles[farmer_y][farmer_x]

    wheat_seeds = item_count(private.get("seeds", {}), "WHEAT")

    # If current tile has a wheat plant, act on it first.
    if isinstance(farmer_tile, dict) and farmer_tile.get("kind") == "PLANT":
        crop = farmer_tile.get("crop")
        if crop == "WHEAT":
            age = obs["day"] - farmer_tile.get("planted_day", obs["day"])
            if age >= CROP_DATA["WHEAT"]["first_yield_day"]:
                return {"farmer": ["HARVEST"], "hands": [], "market": market}
            if not farmer_tile.get("watered_today", False):
                return {"farmer": ["WATER"], "hands": [], "market": market}

    # Find any wheat plant that must be watered or harvested.
    water_targets = []
    harvest_targets = []
    empty_targets = []
    for y in range(height):
        for x in range(width):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                if tile.get("crop") == "WHEAT":
                    age = obs["day"] - tile.get("planted_day", obs["day"])
                    if age >= CROP_DATA["WHEAT"]["first_yield_day"]:
                        harvest_targets.append((x, y))
                    elif not tile.get("watered_today", False):
                        water_targets.append((x, y))
            elif tile is None:
                empty_targets.append((x, y))

    if harvest_targets:
        target = find_nearest((farmer_x, farmer_y), harvest_targets)
        if target == (farmer_x, farmer_y):
            return {"farmer": ["HARVEST"], "hands": [], "market": market}
        return {
            "farmer": [move_towards((farmer_x, farmer_y), target)],
            "hands": [],
            "market": market,
        }

    if water_targets:
        target = find_nearest((farmer_x, farmer_y), water_targets)
        if target == (farmer_x, farmer_y):
            return {"farmer": ["WATER"], "hands": [], "market": market}
        return {
            "farmer": [move_towards((farmer_x, farmer_y), target)],
            "hands": [],
            "market": market,
        }

    if wheat_seeds > 0 and empty_targets:
        target = find_nearest((farmer_x, farmer_y), empty_targets)
        if target == (farmer_x, farmer_y):
            return {"farmer": ["PLANT", "WHEAT"], "hands": [], "market": market}
        return {
            "farmer": [move_towards((farmer_x, farmer_y), target)],
            "hands": [],
            "market": market,
        }

    return {"farmer": ["PASS"], "hands": [], "market": market}


def agent(obs):
    """Main agent entry point for Kaggriculture."""
    return step_marketable_actions(obs)
