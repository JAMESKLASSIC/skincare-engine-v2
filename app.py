import streamlit as st
import pandas as pd

# Page config
st.set_page_config(page_title="Skin Recommendation Engine", layout="centered")

# Visible welcome header
st.title("Welcome to Skin Recommendation Engine")

# Demo Mode toggle (visible only to you)
demo_mode = st.checkbox("Demo Mode (hide for real users)", value=True)
if demo_mode:
    st.info("This demo is using a seller's uploaded inventory. In production, this would be integrated directly into your store.")

# Dynamic CSV loader
st.subheader("Load Product Inventory")
use_default = st.radio("Which inventory?", ("Default (skincare_products_fixed.csv)", "Upload seller's CSV"))

if use_default == "Default (skincare_products_fixed.csv)":
    @st.cache_data
    def load_default():
        try:
            df = pd.read_csv("skincare_products_fixed.csv", encoding='utf-8', on_bad_lines='warn')
            print(f"Loaded default: {len(df)} products")
            return df
        except Exception as e:
            st.error(f"Default CSV error: {str(e)}")
            return pd.DataFrame()
    df = load_default()
else:
    uploaded_file = st.file_uploader("Upload seller's CSV", type=["csv"])
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8', on_bad_lines='warn')
            st.success(f"Loaded {len(df)} products")
            with st.expander("Preview first 5 rows"):
                st.dataframe(df.head())
        except Exception as e:
            st.error(f"Upload error: {str(e)}")
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

if df.empty:
    st.warning("No products loaded. Upload or use default.")
    st.stop()

# Safety check
def is_safe(row, is_sensitive=False, is_pregnant=False, using_prescription=False):
    try:
        if is_pregnant and (row.get('contains_retinol', '') == 'Yes' or row.get('prescription_only', '') == 'Yes'):
            return False
        if is_sensitive and row.get('safe_for_sensitive', '') != 'Yes':
            return False
        if using_prescription and (row.get('contains_retinol', '') == 'Yes' or row.get('contains_acid', '') == 'Yes'):
            return False
        return True
    except:
        return False  # Fail-safe

# Pick product
def pick_product(step_df, fallback_text, risk_flag=None):
    if step_df.empty:
        return fallback_text, None

    if risk_flag == "Sensitive":
        safe = step_df[step_df['safe_for_sensitive'] == 'Yes']
        row = safe.sample(1).iloc[0] if not safe.empty else step_df.sample(1).iloc[0]
    else:
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
        if area == "Face":
            filtered = df[~df['name'].str.lower().str.contains('body', na=False)]
        elif area == "Body":
            filtered = df[df['name'].str.lower().str.contains('body', na=False)]
        else:
            filtered = df.copy()

        filtered = filtered[filtered.apply(lambda row: is_safe(row, is_sensitive, is_pregnant, using_prescription), axis=1)]

        type_pattern = 'All'
        if skin_type == "Oily":
            type_pattern += '|Oily|Acne-prone'
        elif skin_type == "Dry":
            type_pattern += '|Dry'
        filtered = filtered[filtered['suitable_skin_types'].str.contains(type_pattern, case=False, na=True)]

        if filtered.empty:
            filtered = df[df.apply(lambda row: is_safe(row, is_sensitive, is_pregnant, using_prescription), axis=1)]

        if not concerns:
            concerns = ["acne"] if skin_type == "Oily" else ["dryness"] if skin_type == "Dry" else ["dull"]

        if concerns:
            filtered = filtered.reset_index(drop=True)
            mask = pd.Series([False] * len(filtered))
            for c in concerns:
                if c == "acne":
                    keywords = "acne|blemish|pore|salicylic|benzoyl|breakout|niacinamide|oil control"
                elif c == "dark spots / uneven tone":
                    keywords = "brightening|even tone|fade spots|whitening|hyperpigmentation|dark spots|melasma|pigment|arbutin|kojic|niacinamide|vitamin c|tranexamic|azelaic|licorice|thiamidol"
                elif c == "dryness":
                    keywords = "hydration|hyaluronic|moisturizing|dryness|ceramide"
                else:
                    keywords = ""
                if keywords:
                    mask |= filtered['primary_target'].str.contains(keywords, case=False, na=False)
                    mask |= filtered['secondary_target'].str.contains(keywords, case=False, na=False)
                    mask |= filtered['key_actives'].str.contains(keywords, case=False, na=False)
            filtered = filtered[mask]

        if filtered.empty:
            filtered = df[df.apply(lambda row: is_safe(row, is_sensitive, is_pregnant, using_prescription), axis=1)]

        routine = {}

        cleansers = filtered[filtered['step'].str.contains('cleanse', case=False, na=False)]
        routine['Cleanse'], _ = pick_product(cleansers, "Gentle gel or cream cleanser", "Sensitive" if is_sensitive else None)

        toners = filtered[filtered['step'].str.contains('tone|exfoliate', case=False, na=False)]
        routine['Tone'], _ = pick_product(toners, "Hydrating, alcohol-free toner", "Sensitive" if is_sensitive else None)

        treats = filtered[filtered['step'].str.contains('treat', case=False, na=False)]
        if not treats.empty:
            if any("acne" in c for c in concerns):
                acne_treats = treats[treats['key_actives'].str.contains('salicylic|benzoyl|niacinamide', case=False, na=False)]
                routine['Treat'], _ = pick_product(acne_treats if not acne_treats.empty else treats, "Serum for acne")
            elif any("dark spot" in c or "melasma" in c for c in concerns):
                pigment_treats = treats[treats['key_actives'].str.contains('arbutin|tranexamic|niacinamide|vitamin c|azelaic|licorice', case=False, na=False)]
                routine['Treat'], _ = pick_product(pigment_treats if not pigment_treats.empty else treats, "Serum for pigmentation")
            else:
                routine['Treat'], _ = pick_product(treats, "Targeted serum")
        else:
            routine['Treat'] = "Targeted serum for your concern"

        moist = filtered[filtered['step'].str.contains('moisturize', case=False, na=False)]
        routine['Moisturize'], _ = pick_product(moist, "Suitable moisturizer for your skin type", "Sensitive" if is_sensitive else None)

        routine['Protect'] = "Broad-spectrum SPF 50+ every morning"

        return routine
    except Exception as e:
        st.error(f"Error building routine: {str(e)}")
        return {}

# ────────────────────────────────────────────────
#  MAIN FORM
# ────────────────────────────────────────────────
with st.form("skin_form"):
    st.subheader("How would you describe your skin?")
    skin_option = st.selectbox("Select one:", ["Oily", "Dry", "Combination", "Normal", "Not sure"])

    if skin_option == "Not sure":
        st.info("Quick guide:\n\n"
                "- Oily: shiny, large pores, breakouts\n"
                "- Dry: tight, flaky\n"
                "- Combination: oily T-zone, dry cheeks\n"
                "- Normal: balanced\n\n"
                "Which feels closest?")
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
        st.warning("Safety first! Please consult a doctor or dermatologist before starting new products.")
    elif is_sensitive_val and len(concerns) > 2:
        st.warning("Multiple concerns + sensitivity — professional guidance recommended.")
    else:
        routine = build_routine(
            df, skin_type, concerns, is_sensitive_val, is_pregnant_val, using_prescription_val, area
        )

        st.success("Here's your personalized routine:")
        for step, details in routine.items():
            st.markdown(f"**{step}**  \n{details}")

        st.info("Start one new product at a time. Patch test. Be consistent.")

        if area == "Face":
            st.markdown("---")
            want_body = st.radio("Would you like matching body products that suit your current face challenge?", ("No thanks", "Yes, show me"))
            if want_body == "Yes, show me":
                st.subheader("Matching Body Products")
                body_routine = build_routine(df, skin_type, concerns, is_sensitive_val, is_pregnant_val, using_prescription_val, "Body")
                for step, details in body_routine.items():
                    st.markdown(f"**{step}**  \n{details}")

        # Export button
        st.markdown("---")
        if st.button("Export Routine as PDF (for seller)"):
            st.info("PDF export coming soon — for now screenshot or copy text.")

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
