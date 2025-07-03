import json
import os
from collections import defaultdict

# ========================
# CORE SYSTEM
# ========================
DATA_FILE = "nations.json"
REMINDERS_FILE = "reminders.json"

# Cost tables
PROVINCE_COSTS = {1:5000, 2:3500, 3:2500, 4:1500, 5:1250}
CITY_COSTS = {1:20000, 2:15000, 3:10000, 4:5000, 5:2500}
NUKE_COST = 250000
SILO_COST = 100000
MP_COST_PER_UNIT = 1
PORT_COST = 15000 
BATTALION_SIZE = 2000  # MP per battalion
DEPLOYMENT_COST = 0.5  # 0.5 gold per deployed MP per turn
RAILROAD_COST = 1500  # Cost to build one railroad
POLICIES = {
    "third": {
        "mp_cost_reduction": 0.2,
        "war_recovery": 0.66, 
        "peace_recovery": 0.5,
        "peace_gpt_penalty": -0.15,
        "post_loss_penalty": -0.3,
        "post_loss_duration": 4
    },
    "socialist": {
        "build_cost_reduction": 0.15,
        "manpower_boost": 0.1,
        "war_gpt_penalty": -0.2
    },
    "capitalist": {
        "war_gpt_boost": 0.15,
        "expansion_discount": 150,
        "loan_penalty": 0.35,  # New penalty
        "upgrade_cost_increase": 0.15
    }
}

# MP Generation per 5 turns by province level
MP_GENERATION = {1:500, 2:400, 3:300, 4:200, 5:100}

def init_data():
    return {"nations": {}, "current_turn": 0, "next_id": 1}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            for nation in data["nations"].values():
                nation.setdefault("at_war", False)
                nation.setdefault("mp_losses", 0)
                nation.setdefault("loans", [])
                nation.setdefault("provinces", [])
                nation.setdefault("cities", [])
                nation.setdefault("ports", 0)  # Track number of ports
                nation.setdefault("nukes", 0)
                nation.setdefault("silos", 0)
                nation.setdefault("mp_pool", 25000)
                nation.setdefault("recruited_mp", 10000)  # MP in battalions (2000 MP per battalion)
                nation.setdefault("deployed_mp", 0)   # MP currently deployed
                nation.setdefault("battalions", 0)    # Total battalions (recruited_mp / 2000)
                nation.setdefault("railroads", 0)
                nation.setdefault("debuffs", [])
                nation.setdefault("policy", None)
                nation.setdefault("post_loss_turns", 0)
                nation.setdefault("war_history", [])
            return data
    return init_data()

def load_reminders():
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, 'r') as f:
            return json.load(f)
    return defaultdict(list)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def save_reminders(reminders):
    with open(REMINDERS_FILE, 'w') as f:
        json.dump(reminders, f, indent=2)

# ========================
# COMMAND HANDLERS
# ========================
def reset(data, args):
    if not args:
        print("Usage: reset [turn] [gold] [mp] [provinces]")
        return
    
    print("\nWARNING: This will permanently reset:")
    if "turn" in args: print("- Turn counter to 1")
    if "gold" in args: print("- All nations' gold to 10,000")
    if "mp" in args: print("- All nations' MP to 10,000 (5 battalions)")
    if "provinces" in args: print("- All nations' provinces to starting state")
    
    confirm = input("\nAre you sure? This cannot be undone! (yes/no): ").lower()
    if confirm != "yes":
        print("Reset cancelled")
        return
    
    if "provinces" in args:
        # Full reset
        data["current_turn"] = 0
        for nation in data["nations"].values():
            nation["gold"] = 40000
            nation["mp"] = 25000
            nation["provinces"] = []
            nation["cities"] = []
            nation["loans"] = []
            nation["at_war"] = False
            nation["mp_losses"] = 0
            nation["nukes"] = 0
            nation["silos"] = 0
            nation["debuffs"] = []
    else:
        # Partial reset
        if "turn" in args:
            data["current_turn"] = 0
        for nation in data["nations"].values():
            if "gold" in args:
                nation["gold"] = 50000
            if "mp" in args:
                nation["mp"] = 25000
    
    print("Reset completed")

def addgold(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                data["nations"][nation_id]["gold"] += amount
                print(f"Added {amount} gold")
            else: print("Invalid ID")
        else: print("Usage: addgold [id] [amount]")
    except: print("Usage: addgold [id] [amount]")

def removecity(data, args):
    try:
        if len(args) == 4:
            nation_id, city_level, tile_level, amount = args[0], int(args[1]), int(args[2]), int(args[3])
            if nation_id in data["nations"]:
                nation = data["nations"][nation_id]
                cities_removed = 0
                
                # Create temp list to avoid modifying while iterating
                cities_to_check = nation["cities"].copy()
                
                for city in cities_to_check:
                    if city["level"] == city_level and city["tile_level"] == tile_level and cities_removed < amount:
                        nation["cities"].remove(city)
                        cities_removed += 1
                
                print(f"Removed {cities_removed} level {city_level} cities on level {tile_level} tiles")
                if cities_removed < amount:
                    print(f"Warning: Only found {cities_removed} matching cities (tried to remove {amount})")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: removecity [id] [city_level] [tile_level] [amount]")
    except:
        print("Usage: removecity [id] [city_level] [tile_level] [amount]")

def removegold(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                data["nations"][nation_id]["gold"] = max(0, data["nations"][nation_id]["gold"] - amount)
                print(f"Removed {amount} gold")
            else: print("Invalid ID")
        else: print("Usage: removegold [id] [amount]")
    except: print("Usage: removegold [id] [amount]")

def buildrr(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            cost = amount * RAILROAD_COST
            if data["nations"][nation_id]["gold"] >= cost:
                data["nations"][nation_id]["gold"] -= cost
                data["nations"][nation_id]["railroads"] += amount
                print(f"Built {amount} railroads for {cost} gold")
            else: print("Not enough gold")
        else: print("Usage: buildrr [id] [amount]")
    except: print("Usage: buildrr [id] [amount]")

def createrr(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                data["nations"][nation_id]["railroads"] += amount
                print(f"Added {amount} railroads (admin)")
            else: print("Invalid ID")
        else: print("Usage: createrr [id] [amount]")
    except: print("Usage: createrr [id] [amount]")

def addnation(data, args):
    try:
        name = ' '.join(args[:-1])
        color = args[-1]
        nation_id = str(data["next_id"])
        data["nations"][nation_id] = {
            "name": name, "color": color, "gold": 50000, "mp": 25000,
            "provinces": [], "cities": [], "loans": [],
            "at_war": False, "mp_losses": 0, "nukes": 0,
            "silos": 0, "debuffs": []
        }
        data["next_id"] += 1
        print(f"Created {name} (ID: {nation_id})")
    except:
        print("Usage: addnation [name] [color]")

def removenation(data, args):
    if args and args[0] in data["nations"]:
        name = data["nations"][args[0]]["name"]
        del data["nations"][args[0]]
        print(f"Removed {name} (ID: {args[0]})")
    else:
        print("Usage: removenation [id]")

def buyprovince(data, args):
    try:
        if len(args) == 3:
            nation_id, level, amount = args[0], int(args[1]), int(args[2])
            if nation_id in data["nations"] and level in PROVINCE_COSTS:
                cost = PROVINCE_COSTS[level] * amount
                if data["nations"][nation_id]["gold"] >= cost:
                    data["nations"][nation_id]["gold"] -= cost
                    data["nations"][nation_id]["provinces"].extend([{
                        "level": level,
                        "mp_generation": MP_GENERATION[level]
                    } for _ in range(amount)])
                    print(f"Bought {amount} level {level} provinces for {cost} gold")
                else:
                    print("Not enough gold")
            else:
                print("Invalid nation ID or province level (1-5)")
        else:
            print("Usage: buyprovince [id] [level] [amount]")
    except:
        print("Usage: buyprovince [id] [level] [amount]")

def addprovince(data, args):
    try:
        if len(args) == 3:
            nation_id, level, amount = args[0], int(args[1]), int(args[2])
            if nation_id in data["nations"] and level in PROVINCE_COSTS:
                data["nations"][nation_id]["provinces"].extend([{
                    "level": level,
                    "mp_generation": MP_GENERATION[level]
                } for _ in range(amount)])
                print(f"Added {amount} level {level} provinces (admin)")
            else:
                print("Invalid nation ID or province level (1-5)")
        else:
            print("Usage: addprovince [id] [level] [amount]")
    except:
        print("Usage: addprovince [id] [level] [amount]")

def removeprovince(data, args):
    try:
        if len(args) == 3:
            nation_id, level, amount = args[0], int(args[1]), int(args[2])
            if nation_id in data["nations"] and level in PROVINCE_COSTS:
                provinces = data["nations"][nation_id]["provinces"]
                # Remove provinces of specified level
                removed = 0
                for p in provinces[:]:
                    if p["level"] == level and removed < amount:
                        provinces.remove(p)
                        removed += 1
                print(f"Removed {removed} level {level} provinces")
            else:
                print("Invalid nation ID or province level (1-5)")
        else:
            print("Usage: removeprovince [id] [level] [amount]")
    except:
        print("Usage: removeprovince [id] [level] [amount]")

def renovateprovince(data, args):
    try:
        if len(args) == 4:
            nation_id, current_level, new_level, amount = args[0], int(args[1]), int(args[2]), int(args[3])
            
            if nation_id not in data["nations"]:
                print("Error: Invalid nation ID")
                return
            
            if current_level not in PROVINCE_COSTS or new_level not in PROVINCE_COSTS or new_level >= current_level:
                print("Error: Invalid province levels (must upgrade to higher level)")
                return
            
            nation = data["nations"][nation_id]
            cost = (PROVINCE_COSTS[new_level] - PROVINCE_COSTS[current_level]) * amount
            
            # Count matching provinces
            matching = [p for p in nation["provinces"] if p["level"] == current_level]
            if len(matching) < amount:
                print(f"Only {len(matching)} level {current_level} provinces (need {amount})")
                return
            
            if nation["gold"] >= cost:
                nation["gold"] -= cost
                upgraded = 0
                for p in nation["provinces"]:
                    if p["level"] == current_level and upgraded < amount:
                        p["level"] = new_level
                        p["mp_generation"] = MP_GENERATION[new_level]
                        upgraded += 1
                print(f"Renovated {amount} provinces from level {current_level} to {new_level} for {cost} gold")
            else:
                print(f"Need {cost} gold, but only have {nation['gold']}")
        else:
            print("Usage: renovateprovince [id] [current_level] [new_level] [amount]")
    except:
        print("Usage: renovateprovince [id] [current_level] [new_level] [amount]")

def buildport(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                nation = data["nations"][nation_id]
                cost = amount * PORT_COST
                
                if nation["gold"] >= cost:
                    nation["gold"] -= cost
                    nation["ports"] += amount
                    print(f"Built {amount} port(s) for {cost} gold")
                else:
                    print(f"Need {cost} gold, only have {nation['gold']}")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: buildport [id] [amount]")
    except:
        print("Usage: buildport [id] [amount]")

def addport(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                data["nations"][nation_id]["ports"] += amount
                print(f"Added {amount} port(s) (admin)")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: addport [id] [amount]")
    except:
        print("Usage: addport [id] [amount]")

def deploy(data, args):
    try:
        if len(args) == 2:
            nation_id, battalions = args[0], int(args[1])
            nation = data["nations"][nation_id]
            
            available = nation["recruited_mp"] - nation["deployed_mp"]
            max_deploy = available // BATTALION_SIZE
            
            if battalions <= max_deploy:
                nation["deployed_mp"] += battalions * BATTALION_SIZE
                print(f"Deployed {battalions} battalions ({battalions * BATTALION_SIZE} MP)")
            else:
                print(f"Only {max_deploy} battalions available to deploy")
        else:
            print("Usage: deploy [id] [battalions]")
    except:
        print("Usage: deploy [id] [battalions]")

def upgradeprovince(data, args):
    try:
        if len(args) == 4:
            nation_id, current_level, new_level, amount = args[0], int(args[1]), int(args[2]), int(args[3])
            
            if nation_id not in data["nations"]:
                print("Error: Invalid nation ID")
                return
            
            if current_level not in PROVINCE_COSTS or new_level not in PROVINCE_COSTS or new_level >= current_level:
                print("Error: Invalid province levels (must upgrade to higher level)")
                return
            
            nation = data["nations"][nation_id]
            
            # Count matching provinces
            matching = [p for p in nation["provinces"] if p["level"] == current_level]
            if len(matching) < amount:
                print(f"Only {len(matching)} level {current_level} provinces (need {amount})")
                return
            
            upgraded = 0
            for p in nation["provinces"]:
                if p["level"] == current_level and upgraded < amount:
                    p["level"] = new_level
                    p["mp_generation"] = MP_GENERATION[new_level]
                    upgraded += 1
            print(f"Upgraded {amount} provinces from level {current_level} to {new_level} (admin)")
        else:
            print("Usage: upgradeprovince [id] [current_level] [new_level] [amount]")
    except:
        print("Usage: upgradeprovince [id] [current_level] [new_level] [amount]")

def buildcity(data, args):
    try:
        if len(args) == 3:
            nation_id, city_level, tile_level = args[0], int(args[1]), int(args[2])
            
            if nation_id not in data["nations"]:
                print("Error: Invalid nation ID")
                return
            
            if city_level not in CITY_COSTS or tile_level not in PROVINCE_COSTS:
                print("Error: Both city and tile levels must be 1-5")
                return
            
            cost = CITY_COSTS[city_level]
            nation = data["nations"][nation_id]
            
            if nation["gold"] >= cost:
                nation["gold"] -= cost
                nation["cities"].append({
                    "level": city_level,
                    "tile_level": tile_level
                })
                print(f"Built level {city_level} city on level {tile_level} tile for {cost} gold")
            else:
                print(f"Error: Need {cost} gold, but only have {nation['gold']}")
        else:
            print("Usage: buildcity [id] [city_level(1-5)] [tile_level(1-5)]")
    except:
        print("Usage: buildcity [id] [city_level(1-5)] [tile_level(1-5)]")

def addcity(data, args):
    try:
        if len(args) == 3:
            nation_id, city_level, tile_level = args[0], int(args[1]), int(args[2])
            
            if nation_id not in data["nations"]:
                print("Error: Invalid nation ID")
                return
            
            if city_level not in CITY_COSTS or tile_level not in PROVINCE_COSTS:
                print("Error: Both city and tile levels must be 1-5")
                return
            
            data["nations"][nation_id]["cities"].append({
                "level": city_level,
                "tile_level": tile_level
            })
            print(f"Added level {city_level} city on level {tile_level} tile (admin)")
        else:
            print("Usage: addcity [id] [city_level(1-5)] [tile_level(1-5)]")
    except:
        print("Usage: addcity [id] [city_level(1-5)] [tile_level(1-5)]")

def renovatecity(data, args):
    try:
        if len(args) == 3:
            nation_id, current_level, new_level = args[0], int(args[1]), int(args[2])
            
            if nation_id not in data["nations"]:
                print("Error: Invalid nation ID")
                return
            
            if current_level not in CITY_COSTS or new_level not in CITY_COSTS or new_level >= current_level:
                print("Error: Invalid city levels (must upgrade to higher level)")
                return
            
            nation = data["nations"][nation_id]
            cost = CITY_COSTS[new_level] - CITY_COSTS[current_level]
            
            # Find matching city
            city_found = False
            for city in nation["cities"]:
                if city["level"] == current_level:
                    city_found = True
                    if nation["gold"] >= cost:
                        nation["gold"] -= cost
                        city["level"] = new_level
                        print(f"Renovated city from level {current_level} to {new_level} for {cost} gold")
                        break
                    else:
                        print(f"Need {cost} gold, but only have {nation['gold']}")
                        return
            
            if not city_found:
                print(f"No level {current_level} city found")
        else:
            print("Usage: renovatecity [id] [current_level] [new_level]")
    except:
        print("Usage: renovatecity [id] [current_level] [new_level]")

def upgradecity(data, args):
    try:
        if len(args) == 3:
            nation_id, current_level, new_level = args[0], int(args[1]), int(args[2])
            
            if nation_id not in data["nations"]:
                print("Error: Invalid nation ID")
                return
            
            if current_level not in CITY_COSTS or new_level not in CITY_COSTS or new_level >= current_level:
                print("Error: Invalid city levels (must upgrade to higher level)")
                return
            
            nation = data["nations"][nation_id]
            
            # Find matching city
            city_found = False
            for city in nation["cities"]:
                if city["level"] == current_level:
                    city_found = True
                    city["level"] = new_level
                    print(f"Upgraded city from level {current_level} to {new_level} (admin)")
                    break
            
            if not city_found:
                print(f"No level {current_level} city found")
        else:
            print("Usage: upgradecity [id] [current_level] [new_level]")
    except:
        print("Usage: upgradecity [id] [current_level] [new_level]")

def setpolicy(data, args):
    try:
        if len(args) == 2:
            nation_id, policy = args[0], args[1].lower()
            if nation_id in data["nations"]:
                if policy in POLICIES:
                    data["nations"][nation_id]["policy"] = policy
                    print(f"{data['nations'][nation_id]['name']} is now {policy.upper()}")
                    print(f"Effects: {POLICIES[policy]}")
                else:
                    print("Invalid policy (socialist/capitalist/third)")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: setpolicy [id] [socialist/capitalist/third]")
    except:
        print("Usage: setpolicy [id] [socialist/capitalist/third]")

def war(data, args):
    try:
        if len(args) >= 1 and args[0] in data["nations"]:
            nation = data["nations"][args[0]]
            declaring_war = not nation["at_war"]  # Check if this is a war declaration
            
            # Toggle war status
            nation["at_war"] = not nation["at_war"]
            
            # Auto-deploy all battalions when declaring war
            if declaring_war:
                nation["deployed_mp"] = nation["recruited_mp"]
                print(f"All {nation['battalions']} battalions automatically deployed!")
            
            # Track war outcome if provided
            if len(args) >= 2:
                outcome = args[1].lower()
                if outcome in ["won", "lost", "tie"]:
                    nation["war_history"].append({
                        "turn": data["current_turn"],
                        "outcome": outcome
                    })
                    # Third Position penalty for losses
                    if outcome == "lost" and nation.get("policy") == "third":
                        nation["post_loss_turns"] = POLICIES["third"]["post_loss_duration"]
                        print(f"Vampire Economy activated! -30% GPT for {POLICIES['third']['post_loss_duration']} turns")
            
            # Peace-time demobilization
            if not nation["at_war"]:
                nation["deployed_mp"] = 0
                print("All battalions demobilized during peace")
            
            status = "now at war" if nation["at_war"] else "no longer at war"
            print(f"{nation['name']} is {status}")
            
        else:
            print("Usage: war [id] [won/lost/tie (optional)]")
    except Exception as e:
        print(f"Error in war command: {str(e)}")
        print("Usage: war [id] [won/lost/tie (optional)]")

def loan(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                nation = data["nations"][nation_id]
                gpt = calculate_gpt(nation)
                max_loan = gpt // 2
                if amount <= max_loan:
                    nation["gold"] += amount
                    nation["loans"].append({
                        "amount": amount,
                        "due_turn": data["current_turn"] + 3,
                        "repaid": False
                    })
                    print(f"Loan of {amount} gold given. Repay {amount*1.3:.0f} by turn {data['current_turn']+3}")
                else:
                    print(f"Maximum loan is {max_loan} (half of GPT)")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: loan [id] [amount]")
    except:
        print("Usage: loan [id] [amount]")

def buymp(data, args):
    try:
        if len(args) == 2:
            nation_id, battalions = args[0], int(args[1])
            nation = data["nations"][nation_id]
            mp_cost = battalions * BATTALION_SIZE * MP_COST_PER_UNIT
            
            if nation["mp_pool"] >= battalions * BATTALION_SIZE:
                if nation["gold"] >= mp_cost:
                    nation["gold"] -= mp_cost
                    nation["mp_pool"] -= battalions * BATTALION_SIZE
                    nation["recruited_mp"] += battalions * BATTALION_SIZE
                    nation["battalions"] = nation["recruited_mp"] // BATTALION_SIZE
                    print(f"Recruited {battalions} battalions for {mp_cost} gold")
                else:
                    print(f"Need {mp_cost} gold, have {nation['gold']}")
            else:
                print(f"Not enough MP in pool (need {battalions * BATTALION_SIZE}, have {nation['mp_pool']})")
        else:
            print("Usage: buymp [id] [battalions]")
    except:
        print("Usage: buymp [id] [battalions]")

def killmp(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                mp = min(amount, data["nations"][nation_id]["mp"])
                data["nations"][nation_id]["mp"] -= mp
                data["nations"][nation_id]["mp_losses"] += mp
                print(f"Removed {mp} MP (tracking for regeneration)")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: killmp [id] [amount]")
    except:
        print("Usage: killmp [id] [amount]")

def addmp(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                # Add to MP pool instead of direct MP
                data["nations"][nation_id]["mp_pool"] += amount
                print(f"Added {amount} MP to pool (admin)")
                # Update battalions count if adding recruited MP
                if amount % BATTALION_SIZE == 0:
                    battalions = amount // BATTALION_SIZE
                    data["nations"][nation_id]["recruited_mp"] += amount
                    data["nations"][nation_id]["battalions"] = data["nations"][nation_id]["recruited_mp"] // BATTALION_SIZE
                    print(f"Note: Added {battalions} battalions as full units")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: addmp [id] [amount]")
    except:
        print("Usage: addmp [id] [amount]")

def removemp(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                mp = min(amount, data["nations"][nation_id]["mp"])
                data["nations"][nation_id]["mp"] -= mp
                print(f"Removed {mp} MP (admin)")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: removemp [id] [amount]")
    except:
        print("Usage: removemp [id] [amount]")

def addnuke(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                data["nations"][nation_id]["nukes"] += amount
                print(f"Added {amount} nukes to {data['nations'][nation_id]['name']}")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: addnuke [id] [amount]")
    except:
        print("Usage: addnuke [id] [amount]")

def buildnuke(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                cost = amount * NUKE_COST
                if data["nations"][nation_id]["gold"] >= cost:
                    data["nations"][nation_id]["gold"] -= cost
                    data["nations"][nation_id]["nukes"] += amount
                    print(f"Built {amount} nukes for {cost} gold")
                else:
                    print("Not enough gold")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: buildnuke [id] [amount]")
    except:
        print("Usage: buildnuke [id] [amount]")

def nuke(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                if data["nations"][nation_id]["nukes"] >= amount:
                    data["nations"][nation_id]["nukes"] -= amount
                    print(f"Used {amount} nukes from {data['nations'][nation_id]['name']}")
                else:
                    print("Not enough nukes")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: nuke [id] [amount]")
    except:
        print("Usage: nuke [id] [amount]")

def buildsilo(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                data["nations"][nation_id]["silos"] += amount
                print(f"Added {amount} silos to {data['nations'][nation_id]['name']} (admin)")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: buildsilo [id] [amount]")
    except:
        print("Usage: buildsilo [id] [amount]")

def buysilo(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            if nation_id in data["nations"]:
                cost = amount * SILO_COST
                if data["nations"][nation_id]["gold"] >= cost:
                    data["nations"][nation_id]["gold"] -= cost
                    data["nations"][nation_id]["silos"] += amount
                    print(f"Built {amount} silos for {cost} gold")
                else:
                    print("Not enough gold")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: buysilo [id] [amount]")
    except:
        print("Usage: buysilo [id] [amount]")

def debuff(data, args):
    try:
        if len(args) == 3:
            nation_id, percent, turns = args[0], int(args[1]), int(args[2])
            if nation_id in data["nations"]:
                if 0 <= percent <= 100:
                    data["nations"][nation_id]["debuffs"].append({
                        "percent": percent,
                        "expires": data["current_turn"] + turns
                    })
                    print(f"Applied {percent}% GPT debuff for {turns} turns")
                else:
                    print("Percent must be 0-100")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: debuff [id] [percent] [turns]")
    except:
        print("Usage: debuff [id] [percent] [turns]")

def reminder(data, reminders, args):
    if len(args) < 2:
        print("Usage: reminder [turns] \"[message]\"")
        return
    
    try:
        turns = int(args[0])
        message = ' '.join(args[1:])  # Join all remaining arguments
        
        # Basic validation
        if turns <= 0:
            print("Turn count must be positive")
            return
        if not message.strip():
            print("Message cannot be empty")
            return
            
        trigger_turn = data["current_turn"] + turns
        reminders.setdefault(str(trigger_turn), []).append(message)
        save_reminders(reminders)
        print(f"Reminder set for turn {trigger_turn}: \"{message}\"")
        
    except ValueError:
        print("Invalid turn count (must be a number)")
    except Exception as e:
        print(f"Error setting reminder: {str(e)}")

def calculate_gpt(nation):
    # Base income calculations
    province_income = sum({1:1000, 2:700, 3:500, 4:300, 5:250}.get(p["level"], 0) for p in nation["provinces"])
    city_income = sum({1:2000, 2:1500, 3:1000, 4:500, 5:250}.get(c["level"], 0) for c in nation["cities"])
    
    # Apply debuffs
    total_debuff = min(sum(d["percent"] for d in nation["debuffs"]), 100)
    base_gpt = province_income + city_income
    gross_income = int(base_gpt * (100 - total_debuff) / 100)
    
    # Apply policy modifiers
    policy = nation.get("policy")
    if policy == "third":
        if not nation["at_war"]:
            gross_income *= (1 + POLICIES["third"]["peace_gpt_penalty"])
        if nation["post_loss_turns"] > 0:
            gross_income *= (1 + POLICIES["third"]["post_loss_penalty"])
    elif policy == "socialist" and nation["at_war"]:
        gross_income *= (1 + POLICIES["socialist"]["war_gpt_penalty"])
    elif policy == "capitalist" and nation["at_war"]:
        gross_income *= (1 + POLICIES["capitalist"]["war_gpt_boost"])
    
    return int(gross_income)

def process_mp_regeneration(data):
    for nation in data["nations"].values():
        # Passive MP generation from provinces (every 5 turns)
        if data["current_turn"] % 5 == 0:
            mp_generated = sum(MP_GENERATION[p["level"]] for p in nation["provinces"])
            if mp_generated > 0:
                nation["mp"] += mp_generated
                print(f"{nation['name']} generated {mp_generated} MP from provinces")
        
        # Casualty recovery
        if nation["mp_losses"] > 0:
            recovered = nation["mp_losses"] // (2 if nation["at_war"] else 3)
            if recovered > 0:
                nation["mp"] += recovered
                nation["mp_losses"] -= recovered
                print(f"{nation['name']} recovered {recovered} MP from casualties")
        
        # Process debuffs
        nation["debuffs"] = [d for d in nation["debuffs"] if d["expires"] > data["current_turn"]]

def check_reminders(data, reminders):
    current_turn = str(data["current_turn"])
    if current_turn in reminders:
        print("\n=== REMINDERS ===")
        for msg in reminders[current_turn]:
            print(f"- {msg}")
        del reminders[current_turn]
        save_reminders(reminders)

def destroyrr(data, args):
    try:
        if len(args) == 2:
            nation_id, amount = args[0], int(args[1])
            nation = data["nations"][nation_id]
            removed = min(amount, nation["railroads"])
            nation["railroads"] -= removed
            print(f"Permanently destroyed {removed} railroads (no refund)")
        else:
            print("Usage: destroyrr [id] [amount]")
    except:
        print("Usage: destroyrr [id] [amount]")

def provinces(data, args):
    if len(args) != 1:
        print("Usage: provinces [id]")
        return
    
    nation_id = args[0]
    if nation_id not in data["nations"]:
        print("Invalid nation ID")
        return
    
    nation = data["nations"][nation_id]
    
    # Count provinces by level
    province_counts = {1:0, 2:0, 3:0, 4:0, 5:0}
    for p in nation["provinces"]:
        province_counts[p["level"]] += 1
    
    # Count cities by level
    city_counts = {1:0, 2:0, 3:0, 4:0, 5:0}
    for c in nation["cities"]:
        city_counts[c["level"]] += 1
    
    # Print results
    print(f"\n{nation['name']}")
    print("PROVINCES")
    for level in sorted(province_counts.keys()):
        print(f"{level}: {province_counts[level]}")
    
    print("\nCITIES")
    for level in sorted(city_counts.keys()):
        print(f"{level}: {city_counts[level]}")

def buff(data, args):
    try:
        if len(args) == 3:
            nation_id, percent, turns = args[0], int(args[1]), int(args[2])
            if nation_id in data["nations"]:
                if 1 <= percent <= 100 and turns > 0:
                    data["nations"][nation_id]["debuffs"].append({
                        "percent": -percent,  # Negative percent = boost
                        "expires": data["current_turn"] + turns
                    })
                    print(f"Added +{percent}% GPT boost for {turns} turns to {data['nations'][nation_id]['name']}")
                else:
                    print("Percent must be 1-100 and turns must be positive")
            else:
                print("Invalid nation ID")
        else:
            print("Usage: buff [id] [percent] [turns]")
    except:
        print("Usage: buff [id] [percent] [turns]")

def list_nations(data):
    print("\n=== NATIONS ===")
    for id, nation in data["nations"].items():
        gpt = calculate_gpt(nation)
        debuffs = sum(d["percent"] for d in nation["debuffs"])
        policy = str(nation.get("policy", "None")).title()
        
        print(f"\nID: {id} | {nation['name']} [{'WAR' if nation['at_war'] else 'Peace'}]")
        print(f"Policy: {policy}")
        print(f"Gold: {nation['gold']} (+{gpt}/turn){f' (-{debuffs}% debuff)' if debuffs else ''}")
        print(f"Manpower Pool: {nation['mp_pool']}")
        print(f"Military:")
        print(f"  Deployed: {nation['deployed_mp']} MP ({nation['deployed_mp']//BATTALION_SIZE} battalions)")
        print(f"  Reserve: {nation['recruited_mp'] - nation['deployed_mp']} MP ({(nation['recruited_mp'] - nation['deployed_mp'])//BATTALION_SIZE} battalions)")
        print(f"  Losses: {nation['mp_losses']} MP")
        print(f"Ports: {nation.get('ports', 0)}")
        print(f"Nukes: {nation['nukes']} | Silos: {nation['silos']} | Railroads: {nation.get('railroads', 0)}")
        print(f"Provinces: {len(nation['provinces'])} | Cities: {len(nation['cities'])}")

def show_commands():
    print("\n=== NORMAL COMMANDS ===")
    print("Nation Management:")
    print("  provinces [id] - Show province/city distribution by level")
    print("  setpolicy [id] [socialist/capitalist/third]")
    print("  addnation [name] [color]")
    print("\nProvinces:")
    print("  buyprovince [id] [level] [amount]")
    print("  buildport [id] [amount] - Build ports (15000g each)")
    print("  renovateprovince [id] [current] [new] [amount]")
    print("\nCities:")
    print("  buildcity [id] [level] [tile_level]")
    print("  renovatecity [id] [current] [new]")
    print("\nMilitary:")
    print("  war [id]")
    print("  buymp [id] [amount]")
    print("  killmp [id] [amount]")
    print("\nNukes:")
    print("  buildnuke [id] [amount]")
    print("  nuke [id] [amount]")
    print("  deploy [id] [amount]")
    print("  buysilo [id] [amount]")
    print("\nEconomy:")
    print("  loan [id] [amount]")
    print("  buildrr [id] [amount] - Railroads (1500g each)")
    print("\nUtility:")
    print("  reminder [turns] [message]")
    print("  nations")
    print("  turn")
    print("  commands")
    print("  exit")

    print("\n=== ADMIN COMMANDS ===")
    print("  removenation [id]")
    print("  reset [options]")
    print("  addprovince [id] [level] [amount]")
    print("  removeprovince [id] [level] [amount]")
    print("  upgradeprovince [id] [current] [new] [amount]")
    print("  addcity [id] [level] [tile_level]")
    print("  upgradecity [id] [current] [new]")
    print("  addmp [id] [amount]")
    print("  removemp [id] [amount]")
    print("  destroyrr [id] [amount] - Permanent removal")
    print("  buff [id] [percent] [turns]")
    print("  addport [id] [amount] - Add ports (admin)")
    print("  debuff [id] [percent] [turns]")
    print("  addnuke [id] [amount]") 
    print("  removecity [id] [city_level] [tile_level] [amount] - Remove cities (admin)")
    print("  buildsilo [id] [amount]")
    print("  addgold [id] [amount]")
    print("  removegold [id] [amount]")
    print("  createrr [id] [amount] - Railroads (admin)")

def turn(data, reminders):
    data["current_turn"] += 1
    print(f"\n=== TURN {data['current_turn']} ===")
    
    for nation in data["nations"].values():
        # 1. MP Generation (every 5 turns)
        if data["current_turn"] % 5 == 0:
            mp_generated = sum(p["mp_generation"] for p in nation["provinces"])
            if mp_generated > 0:
                nation["mp_pool"] += mp_generated
                print(f"{nation['name']} generated {mp_generated} MP to pool")
        
        # 2. Deployment Maintenance Costs
        if nation["deployed_mp"] > 0:
            cost = int(nation["deployed_mp"] * DEPLOYMENT_COST)
            nation["gold"] -= cost
            print(f"{nation['name']} paid {cost}g for deployed troops")

        # 3. Gold Income and Policy Modifiers
        gross_income = calculate_gpt(nation)
        policy = nation.get("policy")
        
        if policy == "third":
            if not nation["at_war"]:
                gross_income *= (1 + POLICIES["third"]["peace_gpt_penalty"])
            if nation.get("post_loss_turns", 0) > 0:
                gross_income *= (1 + POLICIES["third"]["post_loss_penalty"])
                nation["post_loss_turns"] -= 1
        elif policy == "socialist" and nation["at_war"]:
            gross_income *= (1 + POLICIES["socialist"]["war_gpt_penalty"])
        elif policy == "capitalist" and nation["at_war"]:
            gross_income *= (1 + POLICIES["capitalist"]["war_gpt_boost"])
        
        nation["gold"] += int(gross_income)
        
        # 4. Loan Repayment
        for loan in nation["loans"]:
            if not loan["repaid"] and data["current_turn"] >= loan["due_turn"]:
                repayment = int(loan["amount"] * 1.3)
                if nation["gold"] >= repayment:
                    nation["gold"] -= repayment
                    loan["repaid"] = True
                    print(f"{nation['name']} repaid {repayment} gold")
                else:
                    penalty = POLICIES["capitalist"]["loan_penalty"] if policy == "capitalist" else 0.25
                    penalty_gold = int(nation["gold"] * penalty)
                    nation["gold"] -= penalty_gold
                    print(f"{nation['name']} defaulted! Lost {penalty_gold} gold ({int(penalty*100)}% penalty)")

        # 5. MP Recovery (to pool)
        if nation["mp_losses"] > 0:
            recovery_rate = (
                POLICIES[policy]["war_recovery"] if nation["at_war"] 
                else POLICIES[policy]["peace_recovery"]
            ) if policy == "third" else (0.33 if nation["at_war"] else 0.25)
            
            recovered = int(nation["mp_losses"] * recovery_rate)
            nation["mp_pool"] += recovered  # Goes to pool
            nation["mp_losses"] -= recovered
            if recovered > 0:
                print(f"{nation['name']} recovered {recovered} MP to pool")
    
    check_reminders(data, reminders)
    print("Turn processed!")

# ========================
# MAIN LOOP
# ========================
def main():
    data = load_data()
    reminders = load_reminders()
    print(f"NationStates Manager | Turn {data['current_turn']} | Type 'commands' for help")
    
    while True:
        try:
            cmd = input("\n> ").strip().split()
            if not cmd:
                continue
                
            command, args = cmd[0].lower(), cmd[1:]
            
            if command == "reset":
                reset(data, args)
            elif command == "addnation":
                addnation(data, args)
            elif command == "removenation":
                removenation(data, args)
            elif command == "buyprovince":
                buyprovince(data, args)
            elif command == "provinces":
                provinces(data, args)
            elif command == "addprovince":
                addprovince(data, args)
            elif command == "removeprovince":
                removeprovince(data, args)
            elif command == "renovateprovince":
                renovateprovince(data, args)
            elif command == "upgradeprovince":
                upgradeprovince(data, args)
            elif command == "buildcity":
                buildcity(data, args)
            elif command == "addcity":
                addcity(data, args)
            elif command == "renovatecity":
                renovatecity(data, args)
            elif command == "upgradecity":
                upgradecity(data, args)
            elif command == "war":
                war(data, args)
            elif command == "buildport":
                buildport(data, args)
            elif command == "addport":
                addport(data, args)
            elif command == "loan":
                loan(data, args)
            elif command == "buymp":
                buymp(data, args)
            elif command == "killmp":
                killmp(data, args)
            elif command == "addmp":
                addmp(data, args)
            elif command == "removemp":
                removemp(data, args)
            elif command == "removecity":
                removecity(data, args)
            elif command == "addnuke":
                addnuke(data, args)
            elif command == "buildnuke":
                buildnuke(data, args)
            elif command == "nuke":
                nuke(data, args)
            elif command == "buildsilo":
                buildsilo(data, args)
            elif command == "buysilo":
                buysilo(data, args)
            elif command == "debuff":
                debuff(data, args)
            elif command == "reminder":
                reminder(data, reminders, args)
            elif command == "nations":
                list_nations(data)
            elif command == "commands":
                show_commands()
            elif command == "turn":
                turn(data, reminders)
            elif command == "addgold":
                addgold(data, args)
            elif command == "removegold":
                removegold(data, args)
            elif command == "buildrr":
                buildrr(data, args)
            elif command == "setpolicy":
                setpolicy(data, args)
            elif command == "createrr":
                createrr(data, args)
            elif command == "destroyrr":
                destroyrr(data, args)
            elif command == "deploy":
                deploy(data, args)
            elif command == "buff":
                buff(data, args)
            elif command == "exit":
                save_data(data)
                save_reminders(reminders)
                break
            else:
                print("Invalid command. Type 'commands' for help.")
                
            save_data(data)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()