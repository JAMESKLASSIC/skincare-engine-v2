import streamlit as st
import pandas as pd

st.set_page_config(page_title="Skin Recommendation Engine", layout="centered")

st.title("Welcome to Skin Recommendation Engine")

demo_mode = st.checkbox("Demo Mode (hide for real users)", value=True)
if demo_mode:
    st.info("This demo is using a seller's uploaded inventory. In production, this would be integrated directly into your store.")

# Load inventory
st.subheader("Load Product Inventory")
use_default = st.radio("Which inventory?", ("Default (skincare_products_fixed.csv)", "Upload seller's CSV"))

df = pd.DataFrame()

if use_default == "Default (skincare_products_fixed.csv)":
    try:
        df = pd.read_csv("skincare_products_fixed.csv", encoding='utf-8', on_bad_lines='warn')
        st.success(f"Loaded {len(df)} products")
    except Exception as e:
        st.error(f"Default file error: {str(e)}")
else:
    uploaded_file = st.file_uploader("Upload seller's CSV", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8', on_bad_lines='warn')
            st.success(f"Loaded {len(df)} products")
            with st.expander("Preview"):
                st.dataframe(df.head())
        except Exception as e:
            st.error(f"Upload error: {str(e)}")

if df.empty:
    st.warning("No products loaded. Upload a CSV or use default.")
    st.stop()

# Mojibake cleanup
df['notes'] = df['notes'].astype(str).replace({
    r'â|â': '—',
    r'â': "'",
    r'â|â': '"',
    r'â¢': '•',
    r'â¢': '™',
    r'â¦': '…'
}, regex=True)

def is_safe(row, is_sensitive=False, is_pregnant=False, using_prescription=False):
    if is_pregnant and (row.get('contains_retinol', '') == 'Yes' or row.get('prescription_only', '') == 'Yes'):
        return False
    if using_prescription and (row.get('contains_retinol', '') == 'Yes' or row.get('contains_acid', '') == 'Yes'):
        return False
    if is_sensitive:
        safe_val = row.get('safe_for_sensitive', '').strip().lower()
        if 'no' in safe_val:
            return False
    return True

def get_caution_note(row, is_sensitive):
    if not is_sensitive:
        return ""
    safe_val = row.get('safe_for_sensitive', '').strip().lower()
    if 'caution' in safe_val:
        return " **(Use with caution — patch test recommended; may cause mild irritation in very sensitive skin)**"
    return ""

def pick_product(filtered_df, category_keywords, fallback_text, is_sensitive):
    candidates = filtered_df[
        filtered_df['name'].str.contains(category_keywords, case=False, na=False) |
        filtered_df['notes'].str.contains(category_keywords, case=False, na=False) |
        filtered_df['key_actives'].str.contains(category_keywords, case=False, na=False) |
        filtered_df['primary_target'].str.contains(category_keywords, case=False, na=False) |
        filtered_df['secondary_target'].str.contains(category_keywords, case=False, na=False)
    ]

    if candidates.empty:
        candidates = filtered_df

    if candidates.empty:
        return fallback_text, None

    row = candidates.sample(1).iloc[0]

    caution = get_caution_note(row, is_sensitive)

    details = (
        f"**{row['product_id']} — {row['name']}**  \n"
        f"**Recommended time:** {row.get('recommended_time', 'Anytime')}  \n"
        f"**Max frequency:** {row.get('max_frequency', 'Daily')}  \n"
        f"**How to use:** {row.get('step', 'Follow product instructions')}  \n"
        f"**Notes:** {row.get('notes', 'No extra notes')}{caution}"
    )
    return details, row['product_id']

def build_routine(df, skin_type, concerns, is_sensitive, is_pregnant, using_prescription, area):
    filtered = df.copy()

    if area == "Face":
        filtered = filtered[~filtered['name'].str.lower().str.contains('body', na=False)]
    elif area == "Body":
        filtered = filtered[filtered['name'].str.lower().str.contains('body', na=False)]

    filtered = filtered[filtered.apply(lambda row: is_safe(row, is_sensitive, is_pregnant, using_prescription), axis=1)]

    type_pattern = 'All'
    if skin_type == "Oily":
        type_pattern += '|Oily|Acne-prone'
    elif skin_type == "Dry":
        type_pattern += '|Dry'
    filtered = filtered[filtered['suitable_skin_types'].str.contains(type_pattern, case=False, na=True)]

    if filtered.empty:
        st.warning("No safe products match your profile.")
        return {}

    if concerns:
        keep_rows = pd.Series(False, index=filtered.index)
        for c in concerns:
            if c == "acne":
                k = "acne|blemish|pore|salicylic|benzoyl|breakout|niacinamide|oil control"
            elif c == "dark spots / uneven tone":
                k = "brightening|even tone|fade spots|whitening|hyperpigmentation|dark spots|melasma|pigment|arbutin|kojic|niacinamide|vitamin c|tranexamic|azelaic|licorice"
            elif c == "dryness":
                k = "hydration|hyaluronic|moisturizing|dryness|ceramide"
            else:
                k = ""
            if k:
                keep_rows |= (
                    filtered['primary_target'].str.contains(k, case=False, na=False) |
                    filtered['secondary_target'].str.contains(k, case=False, na=False) |
                    filtered['key_actives'].str.contains(k, case=False, na=False)
                )
        filtered = filtered[keep_rows]

    routine = {}

    routine['Cleanse'] = pick_product(filtered, "cleanser|wash|foam", "Gentle cleanser", is_sensitive)
    routine['Tone'] = pick_product(filtered, "toner|essence", "Hydrating toner", is_sensitive)
    routine['Treat'] = pick_product(filtered, "serum|ampoule|treatment|fade spots|brightening|niacinamide|txa|arbutin|kojic|vitamin c", "Targeted serum", is_sensitive)
    routine['Moisturize'] = pick_product(filtered, "moisturizer|cream|lotion|night cream|hydrator|gel", "Moisturizer", is_sensitive)
    routine['Protect'] = ("Broad-spectrum SPF 50+ every morning", None)

    return routine

# Main form (unchanged)
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
        for step, (details, _) in routine.items():
            st.markdown(f"**{step}**  \n{details}")

        st.info("Start one new product at a time. Patch test. Be consistent.")

        if area == "Face":
            st.markdown("---")
            want_body = st.radio("Would you like matching body products for your face concern?", ("No thanks", "Yes, show me"))
            if want_body == "Yes, show me":
                st.subheader("Matching Body Products")
                body_routine = build_routine(df, skin_type, concerns, is_sensitive_val, is_pregnant_val, using_prescription_val, "Body")
                for step, (details, _) in body_routine.items():
                    st.markdown(f"**{step}**  \n{details}")

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
                st.write(f"**How to use**: {p.get('step', 'Follow product instructions')}")
                st.write(f"**Notes**: {p.get('notes', 'No extra notes')}")

st.caption("Thank you for trusting us with your skin 🌿")
