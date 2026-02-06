
import requests
import json
import sys

def verify():
    # 1. Get Data
    print("Fetching data from Layer 1 (/api/pitwall/view)...")
    try:
        view_res = requests.get("http://localhost:3000/api/pitwall/view?name=sample_laps")
        if view_res.status_code != 200:
            print(f"Layer 1 Failed: {view_res.status_code} {view_res.text}")
            return
        view_data = view_res.json()
        rows = view_data.get('rows', [])
        print(f"Layer 1 Success: Got {len(rows)} rows")
    except Exception as e:
        print(f"Error fetching data: {e}")
        return

    # 2. Construct Payload
    payload = {
        "prompt": "Show me a scatter plot of lap time vs lap number for driver 44",
        "columns": view_data.get("columns", []),
        "sampleRows": rows[:5] 
    }

    # 3. Call Viz
    print("Calling Layer 2 (/api/pitwall/viz)...")
    try:
        viz_res = requests.post("http://localhost:3000/api/pitwall/viz", json=payload)
        print(f"Status Code: {viz_res.status_code}")
        
        if viz_res.status_code == 200:
            try:
                print("Layer 2 Success! Response JSON:")
                print(json.dumps(viz_res.json(), indent=2))
            except:
                print("Layer 2 Response (Not JSON):", viz_res.text)
        else:
            print("Layer 2 Failed:", viz_res.text)
            
    except Exception as e:
        print(f"Error calling viz: {e}")

if __name__ == "__main__":
    verify()
