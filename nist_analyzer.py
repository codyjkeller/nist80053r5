# nist_analyzer.py
import pandas as pd
import argparse
import sys
import os

# --- Configuration ---
# Adjust these column names based on the exact CSV file downloaded from NIST
# Common potential column names:
# Control Identifier, Control (Primary) Identifier, Control ID
CONTROL_ID_COL = 'Control Identifier'
# Control Name, Name
CONTROL_NAME_COL = 'Control Name'
# Control Text, Description
CONTROL_TEXT_COL = 'Control Text'
# Discussion, Guidance
DISCUSSION_COL = 'Discussion'
# Control Family, Family
FAMILY_COL = 'Family'
# Add other columns you might need, e.g., 'Related Controls', baseline columns

# --- Core Functions ---

def load_controls(csv_filepath):
    """
    Loads NIST 800-53 controls from a specified CSV file.

    Args:
        csv_filepath (str): The path to the NIST 800-53 Rev. 5 CSV file.

    Returns:
        pandas.DataFrame: A DataFrame containing the control data,
                          or None if loading fails.
    """
    if not os.path.exists(csv_filepath):
        print(f"Error: CSV file not found at '{csv_filepath}'")
        print("Please download the NIST SP 800-53 Rev. 5 controls CSV "
              "from the official NIST website and place it in the correct location.")
        return None

    try:
        # Attempt to read with standard UTF-8 encoding first
        df = pd.read_csv(csv_filepath, encoding='utf-8')
        print(f"Successfully loaded {len(df)} controls from '{csv_filepath}' (UTF-8).")
    except UnicodeDecodeError:
        try:
            # Fallback to latin-1 encoding if UTF-8 fails
            print("UTF-8 decoding failed, trying latin-1 encoding...")
            df = pd.read_csv(csv_filepath, encoding='latin-1')
            print(f"Successfully loaded {len(df)} controls from '{csv_filepath}' (latin-1).")
        except Exception as e:
            print(f"Error loading CSV file '{csv_filepath}': {e}")
            return None
    except Exception as e:
        print(f"Error loading CSV file '{csv_filepath}': {e}")
        return None

    # --- Data Cleaning and Validation ---
    # Check if essential columns exist
    required_cols = [CONTROL_ID_COL, CONTROL_NAME_COL, CONTROL_TEXT_COL, DISCUSSION_COL, FAMILY_COL]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        print("\nError: The following required columns are missing from the CSV:")
        for col in missing_cols:
            print(f" - '{col}'")
        print("\nPlease check the 'Configuration' section at the top of this script")
        print("and update the column name variables (e.g., CONTROL_ID_COL)")
        print("to match the exact column headers in your downloaded CSV file.")
        print("\nAvailable columns in the CSV:")
        for col in df.columns:
            print(f" - {col}")
        return None

    # Fill NaN values in text fields with empty strings for easier searching
    df[CONTROL_TEXT_COL] = df[CONTROL_TEXT_COL].fillna('')
    df[DISCUSSION_COL] = df[DISCUSSION_COL].fillna('')
    df[CONTROL_NAME_COL] = df[CONTROL_NAME_COL].fillna('')

    # Standardize Control ID format (e.g., uppercase)
    df[CONTROL_ID_COL] = df[CONTROL_ID_COL].str.upper()
    df[FAMILY_COL] = df[FAMILY_COL].str.upper()

    # Set Control ID as index for faster lookups
    df.set_index(CONTROL_ID_COL, inplace=True, drop=False) # Keep the column too

    print(f"Data loaded and preprocessed. Found columns: {', '.join(df.columns)}")
    return df

def get_control_by_id(df, control_id):
    """
    Retrieves a specific control by its identifier.

    Args:
        df (pandas.DataFrame): The DataFrame of controls.
        control_id (str): The control identifier (e.g., 'AC-1', 'AU-2').

    Returns:
        pandas.Series: The control data, or None if not found.
    """
    control_id_upper = control_id.upper()
    if control_id_upper in df.index:
        return df.loc[control_id_upper]
    else:
        print(f"Control ID '{control_id}' not found.")
        return None

def filter_by_family(df, family_id):
    """
    Filters controls by their family identifier.

    Args:
        df (pandas.DataFrame): The DataFrame of controls.
        family_id (str): The family identifier (e.g., 'AC', 'AU').

    Returns:
        pandas.DataFrame: A DataFrame containing controls from the specified family.
    """
    family_id_upper = family_id.upper()
    filtered_df = df[df[FAMILY_COL] == family_id_upper]
    if filtered_df.empty:
         print(f"No controls found for family '{family_id_upper}'.")
    return filtered_df

def search_controls(df, search_term, columns_to_search=None):
    """
    Searches for a term within specified columns of the controls DataFrame.

    Args:
        df (pandas.DataFrame): The DataFrame of controls.
        search_term (str): The term to search for (case-insensitive).
        columns_to_search (list, optional): List of column names to search within.
                                            Defaults to [CONTROL_NAME_COL, CONTROL_TEXT_COL, DISCUSSION_COL].

    Returns:
        pandas.DataFrame: A DataFrame containing controls that match the search term.
    """
    if columns_to_search is None:
        columns_to_search = [CONTROL_NAME_COL, CONTROL_TEXT_COL, DISCUSSION_COL]

    # Ensure only existing columns are searched
    valid_columns = [col for col in columns_to_search if col in df.columns]
    if not valid_columns:
        print(f"Error: None of the specified search columns exist in the DataFrame: {columns_to_search}")
        return pd.DataFrame() # Return empty DataFrame

    # Create a boolean mask for rows where the search term appears in any of the specified columns
    # NaNs were filled earlier, so contains() should work safely.
    mask = df[valid_columns].apply(
        lambda col: col.str.contains(search_term, case=False, na=False)
    ).any(axis=1)

    filtered_df = df[mask]
    if filtered_df.empty:
         print(f"No controls found matching search term '{search_term}'.")
    return filtered_df

def display_control_details(control_series):
    """
    Prints the details of a single control (pandas Series).

    Args:
        control_series (pandas.Series): The control data.
    """
    if control_series is None:
        return

    print("-" * 60)
    print(f"Control ID:   {control_series.name}") # Use index name
    if CONTROL_NAME_COL in control_series:
        print(f"Name:         {control_series[CONTROL_NAME_COL]}")
    if FAMILY_COL in control_series:
        print(f"Family:       {control_series[FAMILY_COL]}")
    print("\nControl Text:")
    if CONTROL_TEXT_COL in control_series:
        print(control_series[CONTROL_TEXT_COL])
    print("\nDiscussion:")
    if DISCUSSION_COL in control_series:
        print(control_series[DISCUSSION_COL])
    # Add more fields as needed
    print("-" * 60)

def display_control_list(df):
    """
    Prints a summary list of controls (ID and Name).

    Args:
        df (pandas.DataFrame): DataFrame of controls to list.
    """
    if df is None or df.empty:
        # Specific messages are printed by the calling functions
        return

    print(f"\nFound {len(df)} control(s):")
    print("-" * 30)
    # Ensure CONTROL_NAME_COL exists before trying to access it
    if CONTROL_NAME_COL in df.columns:
         for control_id, row in df.iterrows():
            print(f"- {control_id}: {row[CONTROL_NAME_COL]}")
    else:
         for control_id in df.index:
            print(f"- {control_id}") # Print only ID if name column is missing
    print("-" * 30)


# --- Command Line Interface ---

def main():
    """
    Main function to parse arguments and execute commands.
    """
    parser = argparse.ArgumentParser(
        description="NIST SP 800-53 Rev. 5 Control Analyzer.",
        epilog="Example: python nist_analyzer.py controls.csv --control-id AC-2"
    )

    parser.add_argument(
        "csv_filepath",
        help="Path to the NIST 800-53 Rev. 5 controls CSV file."
    )
    parser.add_argument(
        "--control-id",
        metavar="ID",
        help="Display details for a specific Control ID (e.g., 'AC-1')."
    )
    parser.add_argument(
        "--family",
        metavar="FAM",
        help="List controls belonging to a specific Family (e.g., 'AC', 'AU')."
    )
    parser.add_argument(
        "--search",
        metavar="TERM",
        help="Search for a term in control name, text, and discussion (case-insensitive)."
    )
    parser.add_argument(
        "--list-all",
        action="store_true", # Doesn't take a value, just checks if flag is present
        help="List all loaded control IDs and names."
    )

    if len(sys.argv) == 2: # Only the script name and csv file path provided
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    # Load the data
    controls_df = load_controls(args.csv_filepath)

    if controls_df is None:
        sys.exit(1) # Exit if loading failed

    # Execute commands based on arguments
    action_taken = False
    if args.control_id:
        control_data = get_control_by_id(controls_df, args.control_id)
        if control_data is not None:
            display_control_details(control_data)
            action_taken = True
    elif args.family:
        filtered_controls = filter_by_family(controls_df, args.family)
        display_control_list(filtered_controls)
        action_taken = True
    elif args.search:
        searched_controls = search_controls(controls_df, args.search)
        display_control_list(searched_controls)
        action_taken = True
    elif args.list_all:
        display_control_list(controls_df)
        action_taken = True

    if not action_taken and len(sys.argv) > 2:
         print("\nNo specific action requested (use --control-id, --family, --search, or --list-all).")
         parser.print_help(sys.stderr)


if __name__ == "__main__":
    main()
