import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field


# Menu cache (memory-based)
# Structure: {cache_key: {"data": menu_data, "expires_at": datetime}}
_menu_cache: Dict[str, Dict] = {}

# Restaurant code mapping
RESTAURANT_NAMES = {
    1: "학생식당",
    2: "숭실도담식당",
    4: "스넥코너",
    5: "푸드코트",
    6: "THE KITCHEN",
    7: "FACULTY LOUNGE",
}


def _get_cache_key(restaurant_code: int, date: str) -> str:
    """Generate cache key"""
    return f"{restaurant_code}_{date}"


def _get_cached_menu(cache_key: str) -> Optional[Dict]:
    """Retrieve menu from cache"""
    if cache_key in _menu_cache:
        cache_entry = _menu_cache[cache_key]
        if datetime.now() < cache_entry["expires_at"]:
            return cache_entry["data"]
        else:
            # Delete expired cache
            del _menu_cache[cache_key]
    return None


def _set_cached_menu(cache_key: str, data: Dict, cache_duration_hours: int = 1):
    """Save menu to cache"""
    _menu_cache[cache_key] = {
        "data": data,
        "expires_at": datetime.now() + timedelta(hours=cache_duration_hours),
    }


def fetch_cafeteria_menu_data(restaurant_code: int, date: str) -> Dict:
    """
    Crawl and parse cafeteria menu from Soongguri website.

    Args:
        restaurant_code: Restaurant code (1-7)
        date: Date in YYYYMMDD format

    Returns:
        Menu data dictionary
    """
    # Check cache
    cache_key = _get_cache_key(restaurant_code, date)
    cached_data = _get_cached_menu(cache_key)
    if cached_data:
        return cached_data

    # Generate URL
    url = f"https://soongguri.com/m/m_req/m_menu.php?rcd={restaurant_code}&sdt={date}"

    try:
        # HTTP request
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Restaurant name
        restaurant_name = RESTAURANT_NAMES.get(
            restaurant_code, f"Restaurant {restaurant_code}"
        )

        # Extract menu data
        menus = []

        # Extract menu info from all tables
        # Menu items are composed of class="menu_nm" and class="menu_list"
        menu_tables = soup.find_all("table")

        for table in menu_tables:
            # Find menu_nm (menu category)
            menu_nm_cells = table.find_all("td", class_="menu_nm")
            menu_list_cells = table.find_all("td", class_="menu_list")

            # Process menu_nm and menu_list in pairs
            for nm_cell, list_cell in zip(menu_nm_cells, menu_list_cells):
                category = nm_cell.get_text(strip=True)

                # Parse menu details
                menu_details = _parse_menu_details(list_cell)

                if menu_details:
                    menus.append(
                        {
                            "category": category,
                            "main_dish": menu_details.get("main_dish", ""),
                            "rating": menu_details.get("rating", ""),
                            "side_dishes": menu_details.get("side_dishes", []),
                            "allergen_info": menu_details.get("allergen_info", ""),
                            "origin_info": menu_details.get("origin_info", ""),
                        }
                    )

        # Compose result data
        result = {
            "restaurant_code": restaurant_code,
            "restaurant_name": restaurant_name,
            "date": date,
            "formatted_date": _format_date(date),
            "menus": menus,
            "total_menus": len(menus),
            "source_url": url,
        }

        # Save to cache (1 hour)
        _set_cached_menu(cache_key, result, cache_duration_hours=1)

        return result

    except requests.exceptions.RequestException as e:
        return {
            "error": f"HTTP request error: {str(e)}",
            "restaurant_code": restaurant_code,
            "restaurant_name": RESTAURANT_NAMES.get(
                restaurant_code, f"Restaurant {restaurant_code}"
            ),
            "date": date,
            "menus": [],
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "restaurant_code": restaurant_code,
            "restaurant_name": RESTAURANT_NAMES.get(
                restaurant_code, f"Restaurant {restaurant_code}"
            ),
            "date": date,
            "menus": [],
        }


def _parse_menu_details(menu_list_cell) -> Optional[Dict]:
    """
    Parse menu details from menu_list cell.

    Args:
        menu_list_cell: BeautifulSoup td element (class="menu_list")

    Returns:
        Menu detail dictionary
    """
    try:
        # Get full text
        full_text = menu_list_cell.get_text(separator="\n", strip=True)

        if not full_text:
            return None

        lines = [line.strip() for line in full_text.split("\n") if line.strip()]

        # Step 1: Extract individual main dishes (after ★ markers)
        individual_dishes = []
        i = 0
        while i < len(lines):
            line = lines[i]
            # If line is just a star, next line is the dish name
            if line == "★":
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # Make sure it's not a star and not a special line
                    if (
                        next_line != "★"
                        and not next_line.startswith("*")
                        and not next_line.startswith("[")
                    ):
                        individual_dishes.append(next_line)
                        i += 2
                        continue
            # If line contains star with dish name
            elif "★" in line:
                dish = line.replace("★", "").strip()
                if dish and not dish.startswith("*") and not dish.startswith("["):
                    individual_dishes.append(dish)
            i += 1

        # Step 2: Find the combined main dish line (format: "dish1, dish2")
        # This line appears after all the individual ★ lines and usually contains comma
        main_dish = ""
        main_dish_line_idx = -1

        for i, line in enumerate(lines):
            # Skip if it's a star line, allergen/origin, or corner name
            if (
                "★" in line
                or line.startswith("*")
                or line.startswith("[")
                or line.endswith("]")
            ):
                continue

            # Check if this line contains all individual dishes combined
            if individual_dishes and "," in line:
                # Check if all dishes appear in this line
                line_lower = line.lower()
                if all(dish.lower() in line_lower for dish in individual_dishes):
                    # Extract just the dish names (before any dash or parenthesis)
                    if "-" in line:
                        main_dish = line.split("-")[0].strip()
                    else:
                        main_dish = line.split("(")[0].strip() if "(" in line else line
                    main_dish_line_idx = i
                    break

        # If we didn't find a combined line, just join individual dishes
        if not main_dish and individual_dishes:
            main_dish = ", ".join(individual_dishes)

        # Step 3: Extract rating (look for "-" followed by numbers)
        rating = ""
        for i, line in enumerate(lines):
            # Skip special lines
            if line.startswith("*") or line.startswith("[") or "★" in line:
                continue

            # Case 1: Rating on same line as main dish (e.g., "곰탕, 한식잡채- 6.0")
            if i == main_dish_line_idx and "-" in line:
                parts = line.split("-")
                if len(parts) >= 2:
                    rating_part = parts[-1].strip()
                    if rating_part and rating_part[0].isdigit():
                        rating = rating_part.split()[0]
                        break

            # Case 2: "-" on one line, rating on next line
            if line == "-" and i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line and next_line[0].isdigit():
                    rating = next_line.split()[0]
                    break

        # Step 4: Extract side dishes
        side_dishes = []
        skip_lines = set()

        # Mark lines to skip
        for i, line in enumerate(lines):
            # Skip corner names
            if line.startswith("[") and line.endswith("]"):
                skip_lines.add(i)
            # Skip star markers
            elif line == "★" or "★" in line:
                skip_lines.add(i)
            # Skip individual dish names (already in main_dish)
            elif line in individual_dishes:
                skip_lines.add(i)
            # Skip combined main dish line
            elif i == main_dish_line_idx:
                skip_lines.add(i)
            # Skip dash and rating
            elif line == "-" or (rating and line.startswith(rating)):
                skip_lines.add(i)
            # Skip allergen and origin info
            elif line.startswith("*"):
                skip_lines.add(i)
            # Skip lines with parentheses (usually English translations)
            elif "(" in line or ")" in line:
                skip_lines.add(i)
            # Skip lines that are mostly English (more than 50% ASCII letters)
            elif line:
                ascii_alpha_count = sum(1 for c in line if c.isascii() and c.isalpha())
                total_chars = len(line.replace(" ", ""))
                if total_chars > 0 and ascii_alpha_count / total_chars > 0.5:
                    skip_lines.add(i)

        # Collect side dishes
        for i, line in enumerate(lines):
            if i not in skip_lines and line:
                side_dishes.append(line)

        # Step 5: Extract allergen info
        allergen_info = ""
        for line in lines:
            if line.startswith("*알러지"):
                allergen_info = line.replace("*알러지유발식품:", "").strip()
                break

        # Step 6: Extract origin info
        origin_info = ""
        origin_parts = []
        for line in lines:
            if line.startswith("*원산지"):
                origin_parts.append(line.replace("*원산지:", "").strip())
            elif origin_parts and not line.startswith("*") and ":" in line:
                # Continue collecting origin info on next line
                origin_parts.append(line)
            elif origin_parts:
                break

        if origin_parts:
            origin_info = " ".join(origin_parts)

        return {
            "main_dish": main_dish,
            "rating": rating,
            "side_dishes": side_dishes,
            "allergen_info": allergen_info,
            "origin_info": origin_info,
        }

    except Exception as e:
        print(f"Error parsing menu details: {e}")
        return None


def _format_date(date_str: str) -> str:
    """
    Convert date from YYYYMMDD format to YYYY-MM-DD format.

    Args:
        date_str: Date string in YYYYMMDD format

    Returns:
        Date string in YYYY-MM-DD format
    """
    try:
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        return date_str
    except Exception:
        return date_str


# LLM Agent Tool definition
class FetchCafeteriaMenuArgs(BaseModel):
    restaurant_code: int = Field(
        description="Restaurant code. 1=Student cafeteria, 2=Soongsil Dodam, 4=Snack corner, 5=Food court, 6=THE KITCHEN, 7=FACULTY LOUNGE"
    )
    date: str = Field(
        description="Date to query (YYYYMMDD format, e.g., 20251112)",
        default=datetime.now().strftime("%Y%m%d"),
    )


@tool(args_schema=FetchCafeteriaMenuArgs)
async def fetch_cafeteria_menu(restaurant_code: int, date: str = None) -> str:
    """
    Fetch cafeteria menu for Soongsil University.

    Restaurant codes:
    - 1: Student cafeteria
    - 2: Soongsil Dodam
    - 4: Snack corner
    - 5: Food court
    - 6: THE KITCHEN
    - 7: FACULTY LOUNGE

    Date should be in YYYYMMDD format (e.g., 20251112).
    If date is not specified, today's date will be used.
    """
    # Use today's date if not specified
    if date is None:
        date = datetime.now().strftime("%Y%m%d")

    # Validate restaurant code
    if restaurant_code not in RESTAURANT_NAMES:
        return f"Error: Invalid restaurant code. Please use one of: 1, 2, 4, 5, 6, 7."

    # Fetch menu data
    menu_data = fetch_cafeteria_menu_data(restaurant_code, date)

    # Handle errors
    if "error" in menu_data:
        return f"Failed to fetch menu: {menu_data['error']}"

    # Format result
    result = f"📍 {menu_data['restaurant_name']}\n"
    result += f"📅 {menu_data['formatted_date']}\n"
    result += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    if menu_data["total_menus"] == 0:
        result += "No menu information available.\n"
    else:
        for menu in menu_data["menus"]:
            result += f"【 {menu['category']} 】\n"

            if menu["main_dish"]:
                result += f"★ {menu['main_dish']}"
                if menu["rating"]:
                    result += f" - {menu['rating']}"
                result += "\n"

            if menu["side_dishes"]:
                result += "Side dishes: " + ", ".join(menu["side_dishes"]) + "\n"

            if menu["allergen_info"]:
                result += f"Allergen: {menu['allergen_info']}\n"

            if menu["origin_info"]:
                result += f"Origin: {menu['origin_info']}\n"

            result += "\n"

    return result.strip()


# Test function
if __name__ == "__main__":
    # Test: Fetch today's menu for student cafeteria
    print("=== Cafeteria Menu Test ===")
    today = datetime.now().strftime("%Y%m%d")
    result = fetch_cafeteria_menu_data(restaurant_code=2, date=today)

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"\nRestaurant: {result['restaurant_name']}")
        print(f"Date: {result['formatted_date']}")
        print(f"Total menus: {result['total_menus']}\n")

        for menu in result["menus"]:
            print(f"【 {menu['category']} 】")
            if menu["main_dish"]:
                print(f"  ★ {menu['main_dish']}", end="")
                if menu["rating"]:
                    print(f" - {menu['rating']}")
                else:
                    print()
            if menu["side_dishes"]:
                print(f"  Side: {', '.join(menu['side_dishes'])}")
            if menu["allergen_info"]:
                print(f"  Allergen: {menu['allergen_info']}")
            if menu["origin_info"]:
                print(f"  Origin: {menu['origin_info']}")
            print()
