import streamlit as st
import pandas as pd

st.set_page_config(page_title="Skin Recommendation Engine", layout="centered")

# ────────────────────────────────────────────────
#  VISIBLE WELCOME HEADER (only this shows on page)
# ────────────────────────────────────────────────
st.title("Welcome to Skin Recommendation Engine")

# ────────────────────────────────────────────────
#  LOAD PRODUCTS (no visible message on page)
# ────────────────────────────────────────────────
@st.cache_data
def load_products():
    try:
        df = pd.read_csv(
            "skincare_products_fixed.csv",
            encoding='utf-8',
            on_bad_lines='warn'
        )
        print(f"Loaded {len(df)} products from skincare_products_fixed.csv")  # terminal only
        return df
    except FileNotFoundError:
        st.error("File 'skincare_products_fixed.csv' not found.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading CSV: {str(e)}")
        return pd.DataFrame()

df = load_products()

if df.empty:
    st.stop()

# ────────────────────────────────────────────────
#  HELPER: Pick product with full details
# ────────────────────────────────────────────────
def pick_product(step_df, fallback_text, risk_flag=None):
    if step_df.empty:
        return fallback_text, None

    if risk_flag == "Sensitive":
        safe = step_df[step_df['safe_for_sensitive'] == 'Yes']
        if not safe.empty:
            row = safe.sample(1).iloc[0]
        else:
            row = step_df.sample(1).iloc[0]
    else:
        row = step_df.sample(1).iloc[0]

    details = (
        f"**{row['product_id']} — {row['name']}**\n"
        f"Recommended time: {row.get('recommended_time', 'Anytime')}\n"
        f"Max frequency: {row.get('max_frequency', 'Daily')}\n"
        f"Notes: {row.get('notes', 'No extra notes')}"
    )
    return details, row['product_id']

# ────────────────────────────────────────────────
#  ROUTINE BUILDER
# ────────────────────────────────────────────────
def build_routine(df, skin_type, concerns, is_sensitive, is_pregnant, using_prescription, area):
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

    if not concerns:
        concerns = ["acne"] if skin_type == "Oily" else ["dryness"] if skin_type == "Dry" else ["dull"]

    if concerns:
        filtered = filtered.reset_index(drop=True)
        mask = pd.Series([False] * len(filtered))
        for c in concerns:
            if c == "acne":
                keywords = "acne|blemish|pore|salicylic|benzoyl|breakout|niacinamide|oil control"
            elif c == "dark spots / uneven tone":
                keywords = "brightening|even tone|fade spots|whitening|hyperpigmentation|dark spots|melasma|pigment|arbutin|kojic|niacinamide|vitamin c|tranexamic"
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
    recommended_ids = []

    cleansers = filtered[filtered['step'] == '1. Cleanse']
    details, pid = pick_product(cleansers, "Gentle gel or cream cleanser", "Sensitive" if is_sensitive else None)
    routine['Cleanse'] = details
    if pid: recommended_ids.append(pid)

    toners = filtered[filtered['step'] == '2. Tone/Exfoliate']
    details, pid = pick_product(toners, "Hydrating, alcohol-free toner", "Sensitive" if is_sensitive else None)
    routine['Tone'] = details
    if pid: recommended_ids.append(pid)

    treats = filtered[filtered['step'] == '3. Treat']
    if not treats.empty:
        if "acne" in concerns:
            acne_treats = treats[treats['key_actives'].str.contains('salicylic|benzoyl|niacinamide', case=False, na=False)]
            details, pid = pick_product(acne_treats if not acne_treats.empty else treats, "Serum for acne")
        elif "dark spots / uneven tone" in concerns:
            pigment_treats = treats[treats['key_actives'].str.contains('arbutin|tranexamic|niacinamide|vitamin c', case=False, na=False)]
            details, pid = pick_product(pigment_treats if not pigment_treats.empty else treats, "Serum for pigmentation")
        else:
            details, pid = pick_product(treats, "Targeted serum")
        routine['Treat'] = details
        if pid: recommended_ids.append(pid)
    else:
        routine['Treat'] = "Targeted serum for your concern"

    moist = filtered[filtered['step'] == '4. Moisturize']
    details, pid = pick_product(moist, "Suitable moisturizer for your skin type", "Sensitive" if is_sensitive else None)
    routine['Moisturize'] = details
    if pid: recommended_ids.append(pid)

    routine['Protect'] = "Broad-spectrum SPF 50+ every morning"

    return routine, recommended_ids

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
    concern_main = st.text_input("Tell me freely (e.g., acne and dark spots)")

    st.subheader("Any of these apply to you?")
    sensitive = st.checkbox("My skin reacts easily / is sensitive")
    pregnant = st.checkbox("I’m pregnant or breastfeeding")
    prescription = st.checkbox("I’m currently using prescription products")

    area = st.radio("Where are you shopping today?", ("Face", "Body", "Both"))

    submitted = st.form_submit_button("Get My Routine")

if submitted:
    skin_type = skin_option
    concerns = [concern_main.lower()] if concern_main else []

    if pregnant or prescription:
        st.warning("Safety first! Please consult a doctor or dermatologist before starting new products.")
    elif sensitive and len(concerns) > 2:
        st.warning("Multiple concerns + sensitivity — professional guidance recommended.")
    else:
        routine, rec_ids = build_routine(df, skin_type, concerns, sensitive, pregnant, prescription, area)

        st.success("Here's your personalized routine:")
        for step, details in routine.items():
            st.markdown(f"**{step}**  \n{details}")

        st.info("Start one new product at a time. Patch test. Be consistent.")

        # Body add-on (only for Face shoppers)
        if area == "Face":
            st.markdown("---")
            want_body = st.radio(
                "Would you like matching body products that suit your current face challenge?",
                ("No thanks", "Yes, show me")
            )

            if want_body == "Yes, show me":
                st.subheader("Matching Body Products for Your Concern")
                body_routine, _ = build_routine(df, skin_type, concerns, sensitive, pregnant, prescription, "Body")
                for step, details in body_routine.items():
                    if "Gentle" not in details and "Hydrating" not in details and "Suitable" not in details:
                        st.markdown(f"**{step}**  \n{details}")
                    else:
                        st.write(f"**{step}**  \n{details}")
            else:
                st.info("Recommendation complete. Feel free to shop or rerun the quiz anytime!")

# ────────────────────────────────────────────────
#  SHOPPING MODE
# ────────────────────────────────────────────────
st.markdown("---")
st.subheader("🛒 Browse Products")
query = st.text_input("Search by keyword (e.g., cleanser, niacinamide, vitamin c)")
if query:
    matches = df[df['name'].str.lower().str.contains(query.lower(), na=False)]
    if matches.empty:
        st.info("No matches found. Try another keyword.")
    else:
        for _, p in matches.iterrows():
            with st.expander(f"{p['product_id']} — {p['name']}"):
                st.write(f"**Best for**: {p['primary_target']}")
                st.write(f"**Key ingredients**: {p['key_actives']}")
                st.write(f"**Recommended time**: {p.get('recommended_time', 'Anytime')}")
                st.write(f"**Max frequency**: {p.get('max_frequency', 'Daily')}")
                st.write(f"**Notes**: {p.get('notes', 'No extra notes')}")

st.caption("Thank you for trusting us with your skin 🌿")
