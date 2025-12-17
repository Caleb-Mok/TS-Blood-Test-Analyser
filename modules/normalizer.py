import json
import os
from rapidfuzz import process, fuzz

class Normalizer:
    def __init__(self, target_keys: list):
        """
        :param target_keys: A list of the 'Canonical' names (the exact keys used in your UI/JSON).
        """
        self.target_keys = target_keys
        self.alias_map = self._load_alias_map()
        
    def _load_alias_map(self):
        """
        Loads the alias map from data/aliases.json.
        """
        try:
            # 1. Determine path to data/aliases.json relative to this file
            # Go up one level from 'modules' to root, then into 'data'
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            json_path = os.path.join(base_dir, 'data', 'aliases.json')
            
            with open(json_path, 'r') as f:
                raw_map = json.load(f)
                
            clean_map = {}
            for k, v in raw_map.items():
                clean_map[k.lower().strip()] = v
                
            return clean_map
        except FileNotFoundError:
            print(f"Warning: Alias file not found at {json_path}. Normalizer will rely only on fuzzy matching.")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing aliases.json: {e}")
            return {}

    # Not used anymore but left here just in case
    def normalize(self, extracted_data: dict) -> dict:
        """
        Takes raw data from LLM and returns a dictionary where keys 
        match the target_keys exactly.
        """
        normalized_data = {}
        raw_tests = extracted_data.get("tests", {})

        for llm_name, test_data in raw_tests.items():
            value = test_data.get("value")
            if value is None:
                continue
            
            # Find the matching canonical name
            canonical_name = self._find_best_match(llm_name)
            
            if canonical_name:
                normalized_data[canonical_name] = str(value)
            else:
                # Optional: Print ignored fields for debugging
                print(f"Normalizer: Could not map '{llm_name}'")

        return normalized_data

    def _find_best_match(self, input_name: str):
        """
        Finds the best matching canonical key for a given input name.
        """
        clean_name = input_name.lower().strip()

        # 1. Exact Match Check (Case-insensitive)
        for target in self.target_keys:
            if target.lower() == clean_name:
                return target

        # 2. Alias/Abbreviation Lookup
        if clean_name in self.alias_map:
            return self.alias_map[clean_name]

        # 3. Fuzzy Matching (RapidFuzz)
        # extractOne returns (match, score, index)
        match = process.extractOne(
            input_name, 
            self.target_keys, 
            scorer=fuzz.token_sort_ratio
        )
        
        # Strictness Check
        if match:
            candidate = match[0]
            score = match[1]
            
            # High confidence threshold
            if score >= 90:
                print(f"Normalizer: Fuzzy matched '{input_name}' -> '{candidate}' ({score:.1f}%)")
                return candidate

        print(f"Normalizer: Could not map '{input_name}'")
        return None