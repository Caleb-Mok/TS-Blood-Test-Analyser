import os
import json
import re
class Analyzer:

    def __init__(self, healthy_file="data/healthy_ranges.json"):
        """Load the healthy reference database from JSON."""
        with open(healthy_file, "r", encoding="utf-8") as f:
            self.healthy_data = json.load(f)
        # self.healthy_db = self.load_healthy_data(healthy_file)


    # def load_healthy_data(self, path):
    #     """Load JSON data of healthy test ranges."""
    #     if not os.path.exists(path):
    #         raise FileNotFoundError(f"Healthy range file not found: {path}")
    #     with open(path, "r", encoding="utf-8") as f:
    #         data = json.load(f)

    #     db = {}
    #     for cat in data["categories"]:
    #         for test in cat["tests"]:
    #             name = test["name"].strip()
    #             min_val = test.get("min","")
    #             max_val = test.get("max","")
    #             db[name] = {
    #                 "category": cat["name"],
    #                 "min": min_val,
    #                 "max": max_val,
    #                 "unit": test.get("units", ""),
    #                 "healthy_value": test.get("healthy_value", ""),
    #             }
    #     return db
    

    def analyze(self, raw_data):
        # data is a dict of {param_name: value(raw string from QLineEdit)}
        # return dict of {param_name: status}, and string (summary)
        
        status_dict = {}
        abnormal_tests, borderline_tests, normal_tests, missing_tests, manual_tests = [], [], [], [], []

        for category in self.healthy_data["categories"]:
            for test in category["tests"]:
                test_name = test["name"]
                units = test.get("units", "")
                healthy_val = test.get("healthy_value", "")
                min_val = test.get("min", "")
                max_val = test.get("max", "")
                user_val = raw_data.get(test_name, "").strip()

                if not user_val:  # user didn’t test this
                    status = "empty"
                    missing_tests.append(test_name)
                else:
                    # Try to convert numerical limits
                    try:
                        user_val_num = float(user_val)
                        # min_num, max_num, healthy_num = self.expression_converter(min_val, max_val, healthy_val)
                        # if min_num is None and max_num is None:
                        #     status = "uncheckable"
                        # else:
                        #     status = self.get_status_color(
                        #         user_val_num,
                        #         healthy_num if healthy_num else (min_num + max_num) / 2 if min_num and max_num else user_val_num,
                        #         min_num if min_num is not None else user_val_num,
                        #         max_num if max_num is not None else user_val_num,
                        #     )
                        status = self.get_status_color(
                            user_val_num, healthy_val, min_val, max_val
                        )


                    except Exception as e:
                        print(e)
                        # Non-numeric user input
                        status = "uncheckable"

                # Store status and details
                status_dict[test_name] = {
                    "value": user_val,
                    "min": min_val,
                    "max": max_val,
                    "units": units,
                    "status": status,
                    "healthy_value": healthy_val
                }

                # Sort into categories for summary
                if status == "red":
                    abnormal_tests.append(test_name)
                elif status == "yellow":
                    borderline_tests.append(test_name)
                elif status == "green":
                    normal_tests.append(test_name)
                elif status == "uncheckable":
                    manual_tests.append(test_name)


        # Generate summary text
        summary_lines = []
        if abnormal_tests:
            summary_lines.append(f"❗ Abnormal results found in: {', '.join(abnormal_tests)}.")
        if borderline_tests:
            summary_lines.append(f"⚠️ Slightly outside healthy range: {', '.join(borderline_tests)}.")
        if normal_tests:
            # summary_lines.append(f"✅ Within healthy range: {', '.join(normal_tests[:5])}" +
            #                      ("..." if len(normal_tests) > 5 else ""))
            summary_lines.append(f"✅ Within healthy range: {', '.join(normal_tests)}.")
        if missing_tests:
            # summary_lines.append(f"ℹ️ Tests not performed: {', '.join(missing_tests[:5])}" +
            #                      ("..." if len(missing_tests) > 5 else ""))
            summary_lines.append(f"ℹ️ Tests not performed: {', '.join(missing_tests)}.")

        if not summary_lines:
            summary_lines.append("No valid test data provided.")

        summary_text = "\n".join(summary_lines)

        return status_dict, summary_text
    
    # def generate_sumamry(self, tested, abnormal, missing):
    #     """Generate a short summary sentence."""
    #     total = tested + missing
    #     if tested == 0:
    #         return "No test data provided."
    #     if abnormal == 0:
    #         return f"All {tested} tested parameters are within healthy ranges. {missing} not tested."
    #     else:
    #         return f"{abnormal} out of {tested} tested parameters are outside the healthy range. {missing} were not tested."


    def expression_converter(self, min_val, max_val, healthy_val):
        """Convert alternative expression formats to numeric, e.g. '<35' or '70-110'.
        Returns (min, max, healthy) as floats or None.
        """
        def parse_val(val):
            if val == "" or val is None:
                return None
            val = str(val).strip()
            # Ranges like '70-110'
            if re.match(r"^\d+(\.\d+)?-\d+(\.\d+)?$", val):
                low, high = val.split("-")
                return float(low), float(high)
            # Inequalities like '<35', '>4.7'
            if val.startswith("<"):
                return None, float(val[1:])
            if val.startswith(">"):
                return float(val[1:]), None
            # Extract numeric parts (ignore text)
            try:
                return float(re.findall(r"[-+]?\d*\.?\d+", val)[0])
            except IndexError:
                return None

        # Parse each one
        min_num = parse_val(min_val)
        max_num = parse_val(max_val)
        healthy_num = parse_val(healthy_val)

        # Flatten range outputs if parse_val returned tuple
        if isinstance(min_num, tuple):
            min_num, _ = min_num
        if isinstance(max_num, tuple):
            _, max_num = max_num
        if isinstance(healthy_num, tuple):
            healthy_num = sum(healthy_num) / len(healthy_num)

        return (
            float(min_num) if min_num is not None else None,
            float(max_num) if max_num is not None else None,
            float(healthy_num) if healthy_num is not None else None,
        )

    def unit_converter():
        """Convert units if needed in future."""
        pass

    def not_in_db():
        """Handle parameters not found in healthy DB."""
        """Handle unknown tests not found in healthy.json"""
        return {
            "value": "",
            "min": "",
            "max": "",
            "units": "",
            "status": "unknown",
            "healthy_value": ""
        }

    def get_status_color(self, user_val_num, healthy_str, min_str, max_str, tolerance=0.10):

        """
        Determine health status color based on user value and reference values.
        Logic summary:
        - Value within ±10% of healthy value -> "green"
        - Between ±10% and limit -> "yellow"
        - Beyond limit -> "red"
        - If only max or min is missing, fill sensible defaults.
        - If healthy value is a range (x-y) or inequalities, handle differently with specific warn bands.
        - No numeric reference or invalid format → "check manually"
        """

        # if min_val is None or max_val is None:
        #     return "uncheckable"

        # lower_warn = healthy_val * (1 - tolerance)
        # upper_warn = healthy_val * (1 + tolerance)
        # if user_val < min_val or user_val > max_val:
        #     return "red"
        # elif user_val < lower_warn or user_val > upper_warn:
        #     return "yellow"
        # else:
        #     return "green"

        # Parse numeric or symbolic ranges
        healthy_str = str(healthy_str).strip()
        min_str, max_str = str(min_str).strip(), str(max_str).strip()

        # If both empty -> manual check
        if not healthy_str and not min_str and not max_str:
            return "check manually"

        # Attempt to parse healthy_val
        healthy_num = None
        min_num = self._try_float(min_str)
        max_num = self._try_float(max_str)

        # --- Case 1: plain numeric healthy value ---
        if healthy_str.replace('.', '', 1).isdigit():
            healthy_num = float(healthy_str)

        # --- Case 2: healthy value is a range, e.g. "4-6" or "4–6" ---
        elif re.match(r"^\s*\d+(\.\d+)?\s*[-–]\s*\d+(\.\d+)?\s*$", healthy_str):
            parts = re.split(r"[-–]", healthy_str)
            low, high = float(parts[0]), float(parts[1])
            range_diff = high-low
            min_num = low - (range_diff * 0.1)  # 10% below lower bound
            max_num = high + (range_diff * 0.1)  # 10% above upper bound
            lower_warn = low + (range_diff * 0.1)
            upper_warn = high - (range_diff * 0.1)
            healthy_num = (low + high) / 2

            if user_val_num <= min_num or user_val_num >= max_num:
                return "red"
            elif user_val_num <= lower_warn or user_val_num >= upper_warn:
                return "yellow"
            else:
                return "green"

        # --- Case 3: "<X" type ---
        elif healthy_str.startswith("<"):
            try:
                x = float(healthy_str[1:])
                min_num = 0
                max_num = x * 1.5  # 50% above limit
                healthy_num = x
            except Exception:
                return "check manually"

        # --- Case 4: ">X" type ---
        elif healthy_str.startswith(">"):
            try:
                x = float(healthy_str[1:])
                min_num = x * 0.5  # 50% below limit
                max_num = x * 10   # 1000% above
                healthy_num = x
            except Exception:
                return "check manually"

        # --- Case 5: No healthy, but has min/max ---
        if healthy_num is None:
            if min_num is not None and max_num is not None:
                healthy_num = (min_num + max_num) / 2
            else:
                return "check manually"

        # --- Safety: if no min but has max ---
        if min_num is None and max_num is not None:
            min_num = 0

        # --- Apply color logic ---
        lower_warn = healthy_num * (1 - tolerance)
        upper_warn = healthy_num * (1 + tolerance)


        # Red = beyond limit
        if user_val_num <= min_num or user_val_num >= max_num:
            return "red"

        # Yellow = between ±10% healthy and limits
        elif user_val_num <= lower_warn or user_val_num >= upper_warn:
            return "yellow"

        # Green = within ±10% healthy value
        else:
            return "green"
        
    def _try_float(self, value):
        """Safely convert a string to float if possible."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
