import streamlit as st
import pandas as pd

st.set_page_config(page_title="Skin Recommendation Engine", layout="centered")

st.title("Welcome to Skin Recommendation Engine")

# Demo mode toggle (visible only to you)
demo_mode = st.checkbox("Demo Mode (hide for real users)", value=True)
if demo_mode:
    st.info("This demo is using a seller's uploaded inventory. In production, this would be integrated directly into your store.")

# Dynamic CSV loader
st.subheader("Load Product Inventory")
use_default = st.radio("Which inventory?", ("Default (skincare_products_fixed.csv)", "Upload seller's CSV"))

df = pd.DataFrame()

if use_default == "Default (skincare_products_fixed.csv)":
    try:
        df = pd.read_csv("skincare_products_fixed.csv", encoding='utf-8', on_bad_lines='warn')
        st.success(f"Loaded {len(df)} products from default file")
    except Exception as e:
        st.error(f"Default file error: {str(e)}")
else:
    uploaded_file = st.file_uploader("Upload seller's CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8', on_bad_lines='warn')
            st.success(f"Loaded {len(df)} products from uploaded file")
            with st.expander("Preview first 5 rows"):
                st.dataframe(df.head())
        except Exception as e:
            st.error(f"Upload error: {str(e)}")

if df.empty:
    st.warning("No products loaded. Upload a CSV or use default.")
    st.stop()

# Quick fix for any remaining mojibake in notes (after UTF-8 save)
df['notes'] = df['notes'].astype(str).replace({
    r'â|â': '—',
    r'â': "'",
    r'â|â': '"',
    r'â¢': '•',
    r'â¢': '™',
    r'â¦': '…'
}, regex=True)

# Safety check — now accepts "Yes" and "Yes with caution"
def is_safe(row, is_sensitive=False, is_pregnant=False, using_prescription=False):
    if is_pregnant and (row.get('contains_retinol', '') == 'Yes' or row.get('prescription_only', '') == 'Yes'):
        return False
    if using_prescription and (row.get('contains_retinol', '') == 'Yes' or row.get('contains_acid', '') == 'Yes'):
        return False
    if is_sensitive:
        safe_val = row.get('safe_for_sensitive', '')
        if not (safe_val.startswith('Yes') or 'Yes with caution' in safe_val):
            return False
    return True

# Pick product — prefers matches in step/name/notes, strict fallback to real data only
def pick_product(filtered_df, step_keywords, fallback_text, risk_flag=None, step_name=""):
    # Try step column first
    step_df = filtered_df[filtered_df['step'].str.contains(step_keywords, case=False, na=False)]

    # If no match, look in name/notes for relevant terms
    if step_df.empty:
        if 'moisturize' in step_name.lower() or 'treat' in step_name.lower():
            step_df = filtered_df[
                filtered_df['name'].str.contains('moisturizer|cream|lotion|night cream|serum|ampoule', case=False, na=False) |
                filtered_df['notes'].str.contains('moisturizer|night cream|overnight|daily moisturizer|serum|ampoule|treat|brightening', case=False, na=False)
            ]

    # Ultimate fallback: any product in filtered_df
    if step_df.empty:
        step_df = filtered_df

    if step_df.empty:
        return fallback_text, None

    # Sensitive preference (using the relaxed is_safe)
    row = step_df.sample(1).iloc[0]

    details = (
        f"**{row['product_id']} — {row['name']}**  \n"
        f"**Recommended time:** {row.get('recommended_time', 'Anytime')}  \n"
        f"**Max frequency:** {row.get('max_frequency', 'Daily')}  \n"
        f"**Notes:** {row.get('notes', 'No extra notes')}"
    )
    return details, row['product_id']

# Routine builder
def build_routine(df, skin_type, concerns, is_sensitive, is_pregnant, using_prescription, area):
    try:
        # Area filter
        if area == "Face":
            filtered = df[~df['name'].str.lower().str.contains('body', na=False)]
        elif area == "Body":
            filtered = df[df['name'].str.lower().str.contains('body', na=False)]
        else:
            filtered = df.copy()

        # Safety filter
        filtered = filtered[filtered.apply(lambda row: is_safe(row, is_sensitive, is_pregnant, using_prescription), axis=1)]

        # Skin type filter
        type_pattern = 'All'
        if skin_type == "Oily":
            type_pattern += '|Oily|Acne-prone'
        elif skin_type == "Dry":
            type_pattern += '|Dry'
        filtered = filtered[filtered['suitable_skin_types'].str.contains(type_pattern, case=False, na=True)]

        # Ultimate fallback if empty
        if filtered.empty:
            filtered = df[df.apply(lambda row: is_safe(row, is_sensitive, is_pregnant, using_prescription), axis=1)]
            if filtered.empty:
                st.warning("No safe products match your profile. Try without sensitive filter or consult a professional.")
                return {}

        # Default concern
        if not concerns:
            concerns = ["acne"] if skin_type == "Oily" else ["dryness"] if skin_type == "Dry" else ["dull"]

        # Concerns filter
        if concerns:
            filtered = filtered.reset_index(drop=True)
            mask = pd.Series([False] * len(filtered))
            for c in concerns:
                if c == "acne":
                    keywords = "acne|blemish|pore|salicylic|benzoyl|breakout|niacinamide|oil control"
                elif c == "dark spots / uneven tone":
                    keywords = "brightening|even tone|fade spots|whitening|hyperpigmentation|dark spots|melasma|pigment|arbutin|kojic|niacinamide|vitamin c|tranexamic|azelaic|licorice|fade spots"
                elif c == "dryness":
                    keywords = "hydration|hyaluronic|moisturizing|dryness|ceramide"
                else:
                    keywords = ""
                if keywords:
                    mask |= filtered['primary_target'].str.contains(keywords, case=False, na=False)
                    mask |= filtered['secondary_target'].str.contains(keywords, case=False, na=False)
                    mask |= filtered['key_actives'].str.contains(keywords, case=False, na=False)
            filtered = filtered[mask]

        routine = {}

        # Steps with broader matching
        routine['Cleanse'], _ = pick_product(filtered, "cleanse", "Gentle cleanser", "Sensitive" if is_sensitive else None, "Cleanse")
        routine['Tone'], _ = pick_product(filtered, "tone|exfoliate", "Hydrating toner", "Sensitive" if is_sensitive else None, "Tone")
        routine['Treat'], _ = pick_product(filtered, "treat", "Targeted serum", "Sensitive" if is_sensitive else None, "Treat")
        routine['Moisturize'], _ = pick_product(filtered, "moisturize", "Moisturizer", "Sensitive" if is_sensitive else None, "Moisturize")
        routine['Protect'] = "Broad-spectrum SPF 50+ every morning"

        return routine

    except Exception as e:
        st.error(f"Error building routine: {str(e)}")
        return {}

# Main form
with st.form("skin_form"):
    st.subheader("How would you describe your skin?")
    skin_option = st.selectbox("Select one:", ["Oily", "Dry", "Combination", "Normal", "Not sure"])

    if skin_option == "Not sure":
        st.info("Quick guide:\n\n- Oily: shiny, large pores, breakouts\n- Dry: tight, flaky\n- Combination: oily T-zone, dry cheeks\n- Normal: balanced")
        skin_option = st.selectbox("Best match?", ["Oily", "Dry", "Combination", "Normal"])

    st.subheader("What is the main issue you want to fix right now?")
    concern_options = [
        "Acne / breakouts",
        "Dark spots / uneven tone / melasma",
        "Dryness / dehydration",
        "Texture / rough skin",
        "Aging / fine lines",
        "Sensitivity / irritation",
        "Dull skin",
        "Damaged barrier",
        "None"
    ]
    selected_concerns = st.multiselect("Select all that apply:", concern_options)

    st.subheader("Any of these apply to you?")
    sensitive = st.checkbox("My skin reacts easily / is sensitive")
    pregnant = st.checkbox("I’m pregnant or breastfeeding")
    prescription = st.checkbox("I’m currently using prescription products")

    area = st.radio("Where are you shopping today?", ("Face", "Body", "Both"))

    submitted = st.form_submit_button("Get My Routine", type="primary")

if submitted:
    is_sensitive_val = sensitive
    is_pregnant_val = pregnant
    using_prescription_val = prescription

    skin_type = skin_option
    concerns = [c.lower() for c in selected_concerns if c != "None"]

    if is_pregnant_val or using_prescription_val:
        st.warning("Safety first! Consult a doctor.")
    elif is_sensitive_val and len(concerns) > 2:
        st.warning("Complex concerns + sensitivity — seek professional advice.")
    else:
        routine = build_routine(df, skin_type, concerns, is_sensitive_val, is_pregnant_val, using_prescription_val, area)

        st.success("Here's your personalized routine:")
        for step, details in routine.items():
            st.markdown(f"**{step}**  \n{details}")

        st.info("Start one new product at a time. Patch test. Be consistent.")

        if area == "Face":
            st.markdown("---")
            want_body = st.radio("Would you like matching body products for your face concern?", ("No thanks", "Yes, show me"))
            if want_body == "Yes, show me":
                st.subheader("Matching Body Products")
                body_routine = build_routine(df, skin_type, concerns, is_sensitive_val, is_pregnant_val, using_prescription_val, "Body")
                for step, details in body_routine.items():
                    st.markdown(f"**{step}**  \n{details}")

        # Next goals
        st.markdown("---")
        st.subheader("🌟 Your Next Skin Goals")
        st.write("• Crystal clear skin")
        st.write("• Natural glow")
        st.write("• Youthful bounce")
        st.success("Come back in 4–8 weeks for your upgraded routine. The best is coming! 🔜")

# Shopping mode
st.markdown("---")
st.subheader("🛒 Browse Products")
query = st.text_input("Search by keyword")
if query:
    matches = df[df['name'].str.lower().str.contains(query.lower(), na=False)]
    if matches.empty:
        st.info("No matches found.")
    else:
        for _, p in matches.iterrows():
            with st.expander(f"{p['product_id']} — {p['name']}"):
                st.write(f"**Best for**: {p['primary_target']}")
                st.write(f"**Key ingredients**: {p['key_actives']}")
                st.write(f"**Recommended time**: {p.get('recommended_time', 'Anytime')}")
                st.write(f"**Max frequency**: {p.get('max_frequency', 'Daily')}")
                st.write(f"**Notes**: {p.get('notes', 'No extra notes')}")

st.caption("Thank you for trusting us with your skin 🌿")
