import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Bundle Cost Tracker", layout="wide")
st.title("\U0001F4C8 Bundle Cost Calculator & Impact Tracker")

# --- Upload Section ---
st.sidebar.header("Upload Your Files")
item_file = st.sidebar.file_uploader("Upload Item Cost CSV", type=["csv"])
bundle_file = st.sidebar.file_uploader("Upload Bundle Definitions CSV", type=["csv"])
updated_cost_file = st.sidebar.file_uploader("Upload Updated Costs (Optional)", type=["csv"])

# --- Load fallback defaults if not uploaded ---
def load_default(filename):
    if os.path.exists(filename):
        return pd.read_csv(filename)
    else:
        return pd.DataFrame()

# Load uploaded or fallback
items_df = pd.read_csv(item_file) if item_file else load_default("item_costs.csv")
bundles_df = pd.read_csv(bundle_file) if bundle_file else load_default("bundle_definitions.csv")

if not items_df.empty and not bundles_df.empty:
    # Clean column names
    items_df.columns = items_df.columns.str.strip()
    bundles_df.columns = bundles_df.columns.str.strip()

    # Strip trailing '.0' from item numbers
    items_df['Item Number'] = items_df['Item Number'].astype(str).str.replace(r'\.0$', '', regex=True)
    bundles_df['Child Item #'] = bundles_df['Child Item #'].astype(str).str.replace(r'\.0$', '', regex=True)
    bundles_df['Parent Item #'] = bundles_df['Parent Item #'].astype(str).str.replace(r'\.0$', '', regex=True)

    # Fill missing or non-existent Quantity column with 1
    if 'Quantity' not in bundles_df.columns:
        bundles_df['Quantity'] = 1
    else:
        bundles_df['Quantity'] = pd.to_numeric(bundles_df['Quantity'], errors='coerce').fillna(1)

    st.subheader("\U0001F4CB Item Costs")
    st.dataframe(items_df)

    st.subheader("\U0001F465 Bundle Definitions")
    st.dataframe(bundles_df)

    # --- Cost Calculation ---
    st.subheader("\U0001F4B2 Parent Bundle Cost Calculation")

    missing_items = set()

    def get_cost(item, qty):
        item_cost = items_df.loc[items_df['Item Number'] == item, 'Cost']
        if not item_cost.empty:
            return float(item_cost.values[0]) * qty
        else:
            missing_items.add(item)
            return 0

    # Group by parent and calculate cost based on quantity
    grouped = bundles_df.groupby('Parent Item #').apply(
        lambda df: pd.Series({
            'Child Items': ', '.join(f"{row['Child Item #']} (x{row['Quantity']})" for _, row in df.iterrows()),
            'Total Cost': '$' + str(round(sum(get_cost(row['Child Item #'], row['Quantity']) for _, row in df.iterrows()), 2))
        })
    ).reset_index()

    st.dataframe(grouped[['Parent Item #', 'Child Items', 'Total Cost']])

    if missing_items:
        st.warning("The following child item numbers were not found in the cost file and were treated as $0:")
        st.write(sorted(missing_items))

    # --- Cost Change Detection ---
    if updated_cost_file:
        updated_df = pd.read_csv(updated_cost_file)
    elif os.path.exists("updated_costs.csv"):
        updated_df = pd.read_csv("updated_costs.csv")
    else:
        updated_df = pd.DataFrame()

    if not updated_df.empty:
        updated_df.columns = updated_df.columns.str.strip()
        updated_df['Item Number'] = updated_df['Item Number'].astype(str).str.replace(r'\.0$', '', regex=True)

        st.subheader("\U0001F504 Cost Change Impact")

        # Merge old and new costs
        merged = pd.merge(items_df, updated_df, on="Item Number", how="inner", suffixes=("_Old", "_New"))
        changed_items = merged[merged['Cost_Old'] != merged['Cost_New']]

        if not changed_items.empty:
            st.write("Items with Changed Costs:")
            st.dataframe(changed_items)

            changed_item_set = set(changed_items['Item Number'])
            affected_parents = []

            for _, row in bundles_df.iterrows():
                if row['Child Item #'] in changed_item_set:
                    affected_parents.append(row)

            if affected_parents:
                affected_df = pd.DataFrame(affected_parents)
                affected_df['Cost'] = affected_df['Child Item #'].map(lambda item: updated_df.loc[updated_df['Item Number'] == item, 'Cost'].values[0] if item in updated_df['Item Number'].values else 0)
                affected_df['Total Cost'] = affected_df['Cost'] * affected_df['Quantity']
                summary = affected_df.groupby('Parent Item #').agg({
                    'Child Item #': lambda x: ', '.join(x),
                    'Total Cost': 'sum'
                }).reset_index()
                summary['Total Cost'] = summary['Total Cost'].apply(lambda x: f"${x:.2f}")
                st.write("Parent Bundles Affected by Cost Changes:")
                st.dataframe(summary)
            else:
                st.success("No parent bundles affected by the cost changes.")
        else:
            st.success("No item costs have changed.")
else:
    st.info("Please upload both the Item Cost and Bundle Definitions files to begin.")
