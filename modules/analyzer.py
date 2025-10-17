import os
import json
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
        abnormal_tests = []
        borderline_tests = []
        normal_tests = []
        missing_tests = []
        self.data=raw_data

        for category in self.healthy_data["categories"]:
            for test in category["tests"]:
                test_name = test["name"]
                units = test["units"]
                min_val = test["min"]
                max_val = test["max"]
                healthy_val = test["healthy_value"]
                user_val = self.data[test_name]

                if not user_val:  # user didn’t test this
                    status = "empty"
                    missing_tests.append(test_name)
                else:
                    # Attempt to convert numerical limits
                    try:
                        min_val = float(min_val)
                        max_val = float(max_val)
                        user_val = float(user_val)
                        status = self.get_status_color(user_val , healthy_val, min_val, max_val)
                    except Exception:
                        status = "uncheckable"

                status_dict[test_name] = {
                    "value": user_val,
                    "min": min_val,
                    "max": max_val,
                    "units": units,
                    "status": status,
                    "healthy_value": healthy_val
                }

                if status == "red":
                    abnormal_tests.append(test_name)
                elif status == "yellow":
                    borderline_tests.append(test_name)
                elif status == "green":
                    normal_tests.append(test_name)

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


    def healthy_converter():
        """Convert alternative expression formats to numeric, e.g. '<35' or '70-110'."""
        pass

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


    def get_status_color(self, user_val, healthy_val ,min_val, max_val, tolerance=0.10):

        """Return color based on how far value is from healthy range."""

        lower_warn = healthy_val * (1 - tolerance)
        upper_warn = healthy_val * (1 + tolerance)
        if user_val < min_val or user_val > max_val:
            return "red"
        elif user_val < lower_warn or user_val > upper_warn:
            return "yellow"
        else:
            return "green"