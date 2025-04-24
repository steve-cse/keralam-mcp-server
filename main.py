# server.py
from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
import requests

DAM_DATA_URL = "https://raw.githubusercontent.com/amith-vp/Kerala-Dam-Water-Levels/main/live.json"

# Create an MCP server
mcp = FastMCP("Keralam AI Server")


@mcp.tool("dam_monitor")
def dam_monitor(
    action: Literal["get_dam", "list_all", "check_alerts", "compare"] = "list_all",
    dam_id: Optional[str] = None,
    second_dam_id: Optional[str] = None,
    metric: Optional[Literal["waterLevel", "storagePercentage", "inflow", "totalOutflow"]] = None
) -> str:
    """
    Monitor dam data and provide insights on water levels, storage, inflow and outflow
    
    Args:
        action: The type of monitoring action to perform
            - get_dam: Get detailed information about a specific dam
            - list_all: List all dams with current status
            - check_alerts: Check for any dams with alert conditions
            - compare: Compare two dams on a specific metric
        dam_id: ID of the dam to get information for (required for get_dam and compare)
        second_dam_id: ID of the second dam for comparison (required for compare)
        metric: The metric to compare when using the compare action
        
    Returns:
        Human-readable information about the requested dam data
    """
    if action == "list_all":
        # Fetch all dams data
        dams_data = fetch_all_dams_from_api()
        
        # Format the response
        result = "Current Dam Status Overview:\n\n"
        for dam in dams_data:
            latest_data = dam["data"][-1]  # Assume last entry is most recent
            result += f"• {dam['name']} ({dam['id']}): {latest_data['waterLevel']}m ({latest_data['storagePercentage']}% full)\n"
        
        return result
        
    elif action == "get_dam":
        if not dam_id:
            return "Error: dam_id is required for get_dam action"
            
        # Fetch specific dam data
        dam_data = fetch_dam_data_from_api(dam_id)
        
        if not dam_data:
            return f"No data found for dam ID: {dam_id}"
            
        latest = dam_data["data"][-1]  # Assume last entry is most recent
        
        # Format the response with detailed information
        result = f"## {dam_data['name']} ({dam_data['officialName']})\n\n"
        result += f"**Current Status** (as of {latest['date']}):\n"
        result += f"- Water Level: {latest['waterLevel']}m (FRL: {dam_data['FRL']}m)\n"
        result += f"- Storage: {latest['liveStorage']} MCM ({latest['storagePercentage']}% of capacity)\n"
        result += f"- Inflow: {latest['inflow']} m³/s\n"
        result += f"- Outflow: {latest['totalOutflow']} m³/s (Power: {latest['powerHouseDischarge']} m³/s, Spillway: {latest['spillwayRelease']} m³/s)\n"
        result += f"- Recent Rainfall: {latest['rainfall']} mm\n\n"
        
        # Add alert information
        water_level = float(latest['waterLevel']) if latest['waterLevel'].replace('.', '', 1).isdigit() else 0
        orange_level = float(dam_data['orangeLevel']) if dam_data['orangeLevel'].replace('.', '', 1).isdigit() else 999
        red_level = float(dam_data['redLevel']) if dam_data['redLevel'].replace('.', '', 1).isdigit() else 999
        
        if water_level >= red_level:
            result += "⚠️ **DANGER ALERT**: Water level has reached or exceeded red alert level!\n"
        elif water_level >= orange_level:
            result += "⚠️ **WARNING**: Water level has reached or exceeded orange alert level!\n"
        
        return result
        
    elif action == "check_alerts":
        # Fetch all dams data
        dams_data = fetch_all_dams_from_api()
        
        alerts = []
        for dam in dams_data:
            latest_data = dam["data"][-1]  # Assume last entry is most recent
            
            # Convert values to float for comparison
            water_level = float(latest_data['waterLevel']) if latest_data['waterLevel'].replace('.', '', 1).isdigit() else 0
            blue_level = float(dam['blueLevel']) if dam['blueLevel'].replace('.', '', 1).isdigit() else 999
            orange_level = float(dam['orangeLevel']) if dam['orangeLevel'].replace('.', '', 1).isdigit() else 999
            red_level = float(dam['redLevel']) if dam['redLevel'].replace('.', '', 1).isdigit() else 999
            
            if water_level >= red_level:
                alerts.append(f"🚨 CRITICAL: {dam['name']} is at RED alert level ({water_level}m)")
            elif water_level >= orange_level:
                alerts.append(f"⚠️ WARNING: {dam['name']} is at ORANGE alert level ({water_level}m)")
            elif water_level >= blue_level:
                alerts.append(f"ℹ️ NOTICE: {dam['name']} is at BLUE alert level ({water_level}m)")
        
        if alerts:
            return "Dam Alert Status:\n\n" + "\n".join(alerts)
        else:
            return "No dams currently at alert levels."
            
    elif action == "compare":
        if not dam_id or not second_dam_id:
            return "Error: Both dam_id and second_dam_id are required for comparison"
        if not metric:
            return "Error: metric is required for comparison"
            
        # Fetch data for both dams
        dam1_data = fetch_dam_data_from_api(dam_id)
        dam2_data = fetch_dam_data_from_api(second_dam_id)
        
        if not dam1_data or not dam2_data:
            return "Error: One or both dam IDs are invalid"
            
        dam1_latest = dam1_data["data"][-1]
        dam2_latest = dam2_data["data"][-1]
        
        # Compare the specified metric
        dam1_value = dam1_latest[metric]
        dam2_value = dam2_latest[metric]
        
        # Determine metric unit
        unit = ""
        if metric == "waterLevel":
            unit = "meters"
        elif metric == "storagePercentage":
            unit = "%"
        elif metric in ["inflow", "totalOutflow"]:
            unit = "m³/s"
        
        # Format comparison result
        result = f"Comparison of {metric} between dams:\n\n"
        result += f"• {dam1_data['name']}: {dam1_value} {unit}\n"
        result += f"• {dam2_data['name']}: {dam2_value} {unit}\n\n"
        
        # Try to provide a numerical comparison if values are numeric
        try:
            val1 = float(dam1_value)
            val2 = float(dam2_value)
            diff = abs(val1 - val2)
            if val1 > val2:
                result += f"{dam1_data['name']} is {diff} {unit} higher than {dam2_data['name']}"
            elif val2 > val1:
                result += f"{dam2_data['name']} is {diff} {unit} higher than {dam1_data['name']}"
            else:
                result += f"Both dams have the same {metric} value"
        except:
            result += "Unable to calculate numerical difference"
        
        return result
    
    return "Invalid action specified. Please use 'get_dam', 'list_all', 'check_alerts', or 'compare'."


@mcp.resource("dam://{dam_id}")
def get_dam_data(dam_id: str) -> dict:
    """
    Get data for a specific dam by its ID
    
    Args:
        dam_id: Unique identifier of the dam
        
    Returns:
        Dictionary containing dam information and its latest data
    """
    # In a real implementation, you would make an API call here
    # to fetch the data using the dam_id parameter
    
    # This is a placeholder for the API call
    dam_data = fetch_dam_data_from_api(dam_id)
    
    return dam_data

@mcp.resource("dams://list")
def list_dams() -> list:
    """
    Get a list of all available dams
    
    Returns:
        List of dam basic information including ID, name, and current status
    """
    # In a real implementation, you would make an API call here
    
    # This is a placeholder for the API call
    dams_list = fetch_all_dams_from_api()
    
    return dams_list

# Helper functions (would need to be implemented)
def fetch_dam_data_from_api(dam_id: str) -> dict:
    """Makes an API call to fetch data for a specific dam"""
    
    try:
        response = requests.get(DAM_DATA_URL)
        response.raise_for_status()
        data = response.json()
        dams = data.get("dams", [])
        
        # Search for the dam by ID
        for dam in dams:
            if dam.get("id") == dam_id:
                return dam
        
        print(f"No dam found with ID: {dam_id}")
        return {}
    
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return {}

def fetch_all_dams_from_api() -> list:
    """Makes an API call to fetch a list of all dams"""
    
    try:
        response = requests.get(DAM_DATA_URL)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        return data.get("dams", [])
    
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return []

if __name__ == "__main__":
    mcp.run()