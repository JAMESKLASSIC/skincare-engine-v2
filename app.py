import streamlit as st
import pandas as pd

st.set_page_config(page_title="Skin Recommendation Engine", layout="centered")

@st.cache_data
def load_products():
    try:
        df = pd.read_csv(
            "skincare_products_fixed.csv",
            encoding='utf-8',
            on_bad_lines='warn'
        )
        st.success(f"Loaded {len(df)} products")
        return df
    except FileNotFoundError:
        st.error("File 'skincare_products_fixed.csv' not found. Please upload it.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading CSV: {str(e)}")
        return pd.DataFrame()

df = load_products()

if df.empty:
    st.stop()

# ────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ────────────────────────────────────────────────
def is_safe(row, is_sensitive, is_pregnant, using_prescription):
    if is_pregnant and (row.get('contains_retinol', '') == 'Yes' or row.get('prescription_only', '') == 'Yes'):
        return False
    if is_sensitive and row.get('safe_for_sensitive', '') != 'Yes':
        return False
    if using_prescription and (row.get('contains_retinol', '') == 'Yes' or row.get('contains_acid', '') == 'Yes'):
        return False
    return True


def pick_product(step_df, fallback_text, risk_flag=None):
    if step_df.empty:
        return fallback_text

    if risk_flag == "Sensitive":
        safe = step_df[step_df['safe_for_sensitive'] == 'Yes']
        if not safe.empty:
            row = safe.sample(1).iloc[0]
        else:
            row = step_df.sample(1).iloc[0]
    else:
        row = step_df.sample(1).iloc[0]

    return (
        f"**{row['product_id']} — {row['name']}**\n"
        f"Recommended time: {row.get('recommended_time', 'Anytime')}\n"
        f"Max frequency: {row.get('max_frequency', 'Daily')}\n"
        f"Notes: {row.get('notes', 'No extra notes')}"
    )


# ────────────────────────────────────────────────
#  ROUTINE BUILDER — now shows real usage info
# ────────────────────────────────────────────────
def build_routine(df, skin_type, concerns, is_sensitive, is_pregnant, using_prescription, area):
    # Very relaxed area filter
    if area == "Face":
        filtered = df[~df['name'].str.lower().str.contains('body wash|shower gel', na=False)]
    elif area == "Body":
        filtered = df[df['name'].str.lower().str.contains('body', na=False)]
    else:
        filtered = df.copy()

    # Safety
    filtered = filtered[filtered.apply(lambda row: is_safe(row, is_sensitive, is_pregnant, using_prescription), axis=1)]

    # Very broad skin type filter
    type_pattern = 'All'
    if skin_type == "Oily":
        type_pattern += '|Oily|Acne-prone'
    elif skin_type == "Dry":
        type_pattern += '|Dry'
    filtered = filtered[
        filtered['suitable_skin_types'].str.contains(type_pattern, case=False, na=True)
    ]

    # Default concern
    if not concerns:
        concerns = ["acne"] if skin_type == "Oily" else ["dryness"] if skin_type == "Dry" else ["dull"]

    # Concerns filter — loose
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

    recommended_products = []

    # 1. Cleanse
    cleansers = filtered[filtered['step'].str.contains('Cleanse', na=False)]
    routine_cleanse = pick_product(cleansers, "Gentle gel or cream cleanser", "Sensitive" if is_sensitive else None)
    st.write(f"**1. Cleanse**  \n{routine_cleanse}")
    if "Gentle" not in routine_cleanse:
        recommended_products.append(routine_cleanse.split('\n')[0])

    # 2. Tone
    toners = filtered[filtered['step'].str.contains('Tone|Exfoliate', na=False)]
    routine_tone = pick_product(toners, "Hydrating, alcohol-free toner", "Sensitive" if is_sensitive else None)
    st.write(f"**2. Tone**  \n{routine_tone}")
    if "Hydrating" not in routine_tone:
        recommended_products.append(routine_tone.split('\n')[0])

    # 3. Treat
    treats = filtered[filtered['step'].str.contains('Treat', na=False)]
    if not treats.empty:
        chosen_row = treats.sample(1).iloc[0]
        routine_treat = (
            f"**{chosen_row['product_id']} — {chosen_row['name']}**  \n"
            f"Recommended time: {chosen_row.get('recommended_time', 'Anytime')}  \n"
            f"Max frequency: {chosen_row.get('max_frequency', 'Daily')}  \n"
            f"Notes: {chosen_row.get('notes', 'No extra notes')}"
        )
        st.write(f"**3. Treat**  \n{routine_treat}")
        recommended_products.append(routine_treat.split('\n')[0])
    else:
        st.write("**3. Treat**  \nTargeted serum for your concern")

    # 4. Moisturize
    moisturizers = filtered[filtered['step'].str.contains('Moisturize', na=False)]
    routine_moist = pick_product(moisturizers, "Suitable moisturizer for your skin type", "Sensitive" if is_sensitive else None)
    st.write(f"**4. Moisturize**  \n{routine_moist}")
    if "Suitable" not in routine_moist:
        recommended_products.append(routine_moist.split('\n')[0])

    # 5. Protect
    st.write("**5. Protect**  \nBroad-spectrum SPF 50+ every morning")

    st.info("Start one new product at a time. Patch test. Consistency wins.")

    # ────────────────────────────────────────────────
    #  PRODUCTS GRID — now always shows real picks
    # ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🛒 Products Recommended for You")

    if recommended_products:
        st.write("These are the actual products picked for your routine (with usage info):")
        for item in recommended_products:
            st.markdown(item)
    else:
        st.info("No exact product matches for your exact input — general guidance provided above.")

    # Next Goals teaser
    st.markdown("---")
    st.subheader("🌟 Your Next Skin Goals")
    st.write("• Crystal clear skin")
    st.write("• Natural glow")
    st.write("• Youthful bounce")
    st.success("Come back in 4–8 weeks for your upgraded routine. The best is coming! 🔜")


# ────────────────────────────────────────────────
#  MAIN FORM (same as before)
# ────────────────────────────────────────────────
with st.form("skin_form"):
    st.subheader("Your Skin Type")
    skin_option = st.selectbox("Select:", ["Oily", "Dry", "Combination", "Normal", "Not sure"])

    if skin_option == "Not sure":
        st.info("Quick guide:\n\n"
                "- Oily: shiny, large pores, breakouts\n"
                "- Dry: tight, flaky\n"
                "- Combination: oily T-zone, dry cheeks\n"
                "- Normal: balanced\n\n"
                "Which one feels closest?")
        skin_option = st.selectbox("Best match?", ["Oily", "Dry", "Combination", "Normal"])

    st.subheader("Current Concerns")
    concern_options = [
        "Acne / breakouts",
        "Dark spots / hyperpigmentation / melasma",
        "Dryness / dehydration",
        "Dull skin",
        "Uneven texture / rough skin",
        "Aging / fine lines",
        "Sensitivity / irritation",
        "Damaged barrier",
        "None"
    ]
    selected_concerns = st.multiselect("Select all:", concern_options)

    st.subheader("Any apply?")
    sensitive = st.checkbox("Skin reacts easily")
    pregnant = st.checkbox("Pregnant / breastfeeding")
    prescription = st.checkbox("Using prescription skincare")

    area = st.radio("Shopping for:", ("Face", "Body", "Both"))

    submitted = st.form_submit_button("Get Routine", type="primary")

if submitted:
    concerns_map = {
        "Acne / breakouts": "acne",
        "Dark spots / hyperpigmentation / melasma": "dark spots / uneven tone",
        "Dryness / dehydration": "dryness",
        "Dull skin": "dull",
        "Uneven texture / rough skin": "texture / rough skin",
        "Aging / fine lines": "aging",
        "Sensitivity / irritation": "sensitivity",
        "Damaged barrier": "barrier damage"
    }
    concerns = [concerns_map.get(c) for c in selected_concerns if c != "None"]

    is_sensitive = sensitive
    is_pregnant = pregnant
    using_prescription = prescription

    if is_pregnant or using_prescription:
        st.warning("Safety first! Consult doctor.")
    elif is_sensitive and len(concerns) > 2:
        st.warning("Complex concerns — seek professional advice.")
    else:
        build_routine(df, skin_option, concerns, is_sensitive, is_pregnant, using_prescription, area)

# Shopping section
st.markdown("---")
st.subheader("🛒 Browse Products")
query = st.text_input("Search keyword")
if query:
    matches = df[df['name'].str.lower().str.contains(query.lower(), na=False)]
    if matches.empty:
        st.info("No matches — try another word")
    else:
        for _, p in matches.iterrows():
            with st.expander(f"{p['product_id']} — {p['name']}"):
                st.write(f"Best for: {p['primary_target']}")
                st.write(f"Key actives: {p['key_actives']}")
                st.write(f"Recommended time: {p.get('recommended_time', 'Anytime')}")
                st.write(f"Max frequency: {p.get('max_frequency', 'Daily')}")
                st.write(f"Notes: {p.get('notes', 'No extra notes')}")

st.caption("Thank you for trusting us with your skin 🌿")


