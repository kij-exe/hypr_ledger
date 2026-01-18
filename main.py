import requests
import lz4.frame
import pandas as pd
from io import StringIO


def retrieve_builder_fills(builder_address: str, date: str) -> pd.DataFrame:
    """
    Retrieve builder fills data from Hyperliquid and convert to pandas DataFrame.
    
    Args:
        builder_address: The builder's address (e.g., '0x2868fc0d9786a740b491577a43502259efa78a39')
        date: Date in YYYYMMDD format (e.g., '20250116')
    
    Returns:
        pd.DataFrame: DataFrame containing the builder fills data
    """
    url = f"https://stats-data.hyperliquid.xyz/Mainnet/builder_fills/{builder_address}/{date}.csv.lz4"
    
    # Download the compressed data
    response = requests.get(url)
    response.raise_for_status()
    
    # Decompress the lz4 data
    decompressed_data = lz4.frame.decompress(response.content)
    
    # Convert bytes to string and then to DataFrame
    csv_string = decompressed_data.decode('utf-8')
    df = pd.read_csv(StringIO(csv_string))
    
    return df


def filter_by_user(df: pd.DataFrame, user_address: str) -> pd.DataFrame:
    """
    Filter the builder fills DataFrame by a specific user address.
    
    Args:
        df: DataFrame containing builder fills data
        user_address: The user's address to filter by (e.g., '0x0e09b56ef137f417e424f1265425e93bfff77e17')
    
    Returns:
        pd.DataFrame: Filtered DataFrame containing only rows for the specified user
    """
    return df[df['user'] == user_address]


if __name__ == "__main__":
    # Configuration
    builder_address = "0x2868fc0d9786a740b491577a43502259efa78a39"
    # builder_address = "0xe95a5e31904e005066614247d309e00d8ad753aa"
    user_address = "0x0e09b56ef137f417e424f1265425e93bfff77e17"
    date = "20260116"
    
    # Retrieve data
    print(f"Retrieving builder fills for {builder_address} on {date}...")
    df = retrieve_builder_fills(builder_address, date)
    print(f"Retrieved {len(df)} total records")
    print(f"\nDataFrame shape: {df.shape}")
    print(f"\nColumns: {list(df.columns)}")
    
    # Filter by user
    print(f"\nFiltering by user address: {user_address}...")
    user_df = filter_by_user(df, user_address)
    print(f"Found {len(user_df)} records for this user")
    
    # Display results
    if len(user_df) > 0:
        print(f"\nFiltered data:\n{user_df}")
        # print(f"\nData types:\n{user_df.dtypes}")
    else:
        print("\nNo records found for this user address")
