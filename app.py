import streamlit as st
import pandas as pd

st.set_page_config(page_title="Skin Recommendation Engine", layout="centered")

st.title("Welcome to Skin Recommendation Engine")

demo_mode = st.checkbox("Demo Mode (hide for real users)", value=True)
if demo_mode:
    st.info("This demo is using a seller's uploaded inventory. In production, this would be integrated directly into your store.")

# ────────────────────────────────────────────────
# Load inventory
# ────────────────────────────────────────────────
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
            with st.expander("Preview first 5 rows"):
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

# Ensure category column exists
if 'category' not in df.columns:
    st.warning("No 'category' column found in CSV. Using fallback keyword matching.")
    df['category'] = ""

# ────────────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────────────

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

# Concern keyword mapping
CONCERN_KEYWORDS = {
    "acne": "acne|blemish|pore|salicylic|benzoyl|breakout|niacinamide|oil control",
    "dark spots / uneven tone / melasma": "brightening|even tone|fade spots|whitening|hyperpigmentation|dark spots|melasma|pigment|arbutin|kojic|niacinamide|vitamin c|tranexamic|azelaic|licorice|discoloration|spot fading|tone correcting",
    "dryness / dehydration": "hydration|hyaluronic|moisturizing|dryness|ceramide|glycerin|plumping|humectant",
    "texture / rough skin": "texture|rough|exfoliation|smoothing|glycolic|lactic",
    "aging / fine lines": "anti-aging|retinol|firming|wrinkle",
    "sensitivity / irritation": "sensitive|soothing|gentle|calming|centella|ceramide|barrier",
    "dull skin": "dull|glow|radiance|vitamin c",
    "damaged barrier": "barrier|ceramide|repair|restore"
}

# Category to step mapping (your exact wordings)
CATEGORY_MAPPING = {
    'Cleanse': [
        "Acne Treatment / Cleanser",
        "Cleansing / Balancing / Brightening",
        "Cleansing / Hydrating / Barrier Repair",
        "Cleansing / Refreshing",
        "Cleansing / Makeup Removal / Refreshing",
        "Cleansing / Blemish Control / Barrier Repair",
        "Cleansing / Oil Control / Barrier Repair",
        "Cleansing / Exfoliating / Blemish Control",
        "Feminine Hygiene / Cleansing",
        "Exfoliating / Brightening / Cleansing",
        "Hydrating / Nourishing / Cleansing",
        "Refreshing / Hydrating / Cleansing",
        "Hydrating / Pampering / Cleansing",
        "Exfoliating / Refreshing / Cleansing",
        "Exfoliating / Renewing / Cleansing",
        "Cleansing / Hydrating",
        "Brightening / Cleansing / Bar Soap"
    ],
    'Tone': [
        "Brightening / Tone-Up",
        "Hydrating / Barrier Repair",
        "Hydrating / Plumping / Essence",
        "Hydrating / Plumping / Serum",
        "Brightening / Spot Fading / Essence"
    ],
    'Treat': [
        "Serum / Barrier Repair / Hydrator",
        "Brightening / Antioxidant / Serum",
        "Brightening / Blemish Control / Serum",
        "Brightening / Soothing / Serum",
        "Exfoliating / Brightening / Serum",
        "Anti-Aging / Brightening / Serum",
        "Brightening / Tone Correcting / Serum"
    ],
    'Moisturize': [
        "Exfoliating / Moisturizer",
        "Moisturizer / Body Oil",
        "Moisturizer / Hydrator",
        "Moisturizer / Body Lotion",
        "Moisturizer / Hydrator / Repair",
        "Moisturizer / Balancing / Soothing",
        "Brightening / Tone Correcting / Moisturizer",
        "Brightening / Spot Treatment / Moisturizer",
        "Brightening / Moisturizer / Hydrator",
        "Brightening / Anti-Acne / Moisturizer",
        "Brightening / Moisturizing / Tone Correcting",
        "Moisturizer / Hydrator / Plumping",
        "Moisturizer / Barrier Repair / Hydrator",
        "Moisturizer / Blemish Control / Barrier Repair",
        "Moisturizer / Brightening / Hydrator",
        "Anti-Aging / Firming / Moisturizer",
        "Moisturizer / Barrier Repair / Oil Control",
        "Hydrating / Plumping / Moisturizer",
        "Brightening / Moisturizing / Hydrator",
        "Anti-Aging / Hydrating / Renewing",
        "Anti-Aging / Moisturizer / Smoothing",
        "Moisturizer / Hydrator",
        "Brightening / Moisturizing / Body Oil",
        "Moisturizer / Body Oil / Brightening",
        "Moisturizer / Body Oil / Glow-Boosting",
        "Brightening / Moisturizing / Body Oil Gel",
        "Moisturizer / Hydrator / Body Oil Gel",
        "Brightening / Moisturizing / Multi-Benefit"
    ],
    'Protect': [
        "Sunscreen / UV Protection"
    ]
}

def get_filtered_df(df, skin_type, concerns, is_sensitive, is_pregnant, using_prescription, area):
    filtered = df.copy()

    # Area filter
    if area == "Face":
        filtered = filtered[~filtered['name'].str.lower().str.contains('body|intimate|feminine|femfresh', na=False)]
    elif area == "Body":
        filtered = filtered[filtered['name'].str.lower().str.contains('body', na=False)]

    # Safety
    filtered = filtered[filtered.apply(lambda row: is_safe(row, is_sensitive, is_pregnant, using_prescription), axis=1)]

    # Skin type
    type_pattern = 'All'
    if skin_type == "Oily":
        type_pattern += '|Oily|Acne-prone'
    elif skin_type == "Dry":
        type_pattern += '|Dry'
    filtered = filtered[filtered['suitable_skin_types'].str.contains(type_pattern, case=False, na=True)]

    # Concerns (secondary boost)
    if concerns:
        keep_rows = pd.Series(False, index=filtered.index)
        for concern in concerns:
            concern = concern.lower().strip()
            k = CONCERN_KEYWORDS.get(concern, "")
            if k:
                keep_rows |= (
                    filtered['primary_target'].str.contains(k, case=False, na=False) |
                    filtered['secondary_target'].str.contains(k, case=False, na=False) |
                    filtered['key_actives'].str.contains(k, case=False, na=False) |
                    filtered['notes'].str.contains(k, case=False, na=False)
                )
        filtered = filtered[keep_rows]

    if filtered.empty:
        st.warning("No safe products match your profile.")
        return pd.DataFrame()

    return filtered

def pick_product(filtered_df, step_name, fallback_text, is_sensitive, concerns=None):
    target_categories = CATEGORY_MAPPING.get(step_name, [])
    candidates = filtered_df[filtered_df['category'].isin(target_categories)]

    if candidates.empty:
        return fallback_text, None

    # Secondary boost: score products by concern relevance
    if concerns:
        candidates = candidates.copy()
        candidates['concern_score'] = 0
        for concern in concerns:
            k = CONCERN_KEYWORDS.get(concern, "")
            if k:
                candidates['concern_score'] += (
                    candidates['primary_target'].str.contains(k, case=False, na=False).astype(int) +
                    candidates['secondary_target'].str.contains(k, case=False, na=False).astype(int) +
                    candidates['key_actives'].str.contains(k, case=False, na=False).astype(int) +
                    candidates['notes'].str.contains(k, case=False, na=False).astype(int)
                )
        candidates = candidates.sort_values('concern_score', ascending=False)

    # Take top match
    row = candidates.iloc[0]

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
    filtered = get_filtered_df(df, skin_type, concerns, is_sensitive, is_pregnant, using_prescription, area)
    if filtered.empty:
        return {}

    routine = {}
    routine['Cleanse'] = pick_product(filtered, 'Cleanse', "Gentle cleanser", is_sensitive, concerns)
    routine['Tone'] = pick_product(filtered, 'Tone', "Hydrating toner", is_sensitive, concerns)
    routine['Treat'] = pick_product(filtered, 'Treat', "Targeted serum", is_sensitive, concerns)
    routine['Moisturize'] = pick_product(filtered, 'Moisturize', "Moisturizer", is_sensitive, concerns)
    routine['Protect'] = pick_product(filtered, 'Protect', "Broad-spectrum SPF 50+ every morning", is_sensitive, concerns)

    return routine

# ────────────────────────────────────────────────
# Enhanced personalized skin goals
# ────────────────────────────────────────────────

NEXT_SKIN_GOALS = {
    "acne / breakouts": [
        "Visibly clearer skin with fewer active breakouts",
        "Reduced redness, inflammation and post-blemish marks",
        "Balanced oil production without over-drying",
        "Calmer, less reactive complexion",
        "Smoother texture and minimized pore appearance"
    ],
    "dark spots / uneven tone / melasma": [
        "Visibly more even skin tone",
        "Faded dark spots, sun spots and post-inflammatory marks",
        "Brighter, more luminous complexion",
        "Improved clarity and uniformity",
        "Prevention of new pigmentation with protection"
    ],
    "dryness / dehydration": [
        "Deep, long-lasting hydration – no more tightness",
        "Plump, supple skin with restored moisture",
        "Stronger skin barrier – fewer dry patches",
        "Comfortable, soft feel all day",
        "Healthy, dewy radiance from within"
    ],
    "texture / rough skin": [
        "Noticeably smoother, more refined surface",
        "Reduced roughness, bumps and sandpaper feel",
        "Visibly improved micro-texture",
        "Even, polished-looking skin",
        "Silky, comfortable touch"
    ],
    "aging / fine lines": [
        "Visibly firmer, more lifted contours",
        "Reduced appearance of fine lines & wrinkles",
        "Smoother texture and improved elasticity",
        "Plumper, more youthful-looking volume",
        "Healthier, resilient skin"
    ],
    "sensitivity / irritation": [
        "Calmer, less reactive skin daily",
        "Significant reduction in redness & stinging",
        "Stronger tolerance to triggers",
        "Comfortable, soothed feeling",
        "Restored barrier – fewer flare-ups"
    ],
    "dull skin": [
        "Brighter, more radiant complexion",
        "Healthy, fresh-looking glow",
        "Reduced ashy or tired appearance",
        "Visible luminosity all day",
        "Awake, energized skin tone"
    ],
    "damaged barrier": [
        "Strong, intact skin barrier",
        "Less sensitivity & reactivity",
        "Better moisture retention",
        "Calmer, more resilient skin",
        "Healthy bounce and comfort restored"
    ],
    # Pre-defined common combinations
    "dryness / dehydration+dull skin": [
        "Deep hydration + visible inner glow",
        "Plump, dewy skin that looks rested",
        "Strong moisture barrier + healthy radiance",
        "Soft, luminous complexion without tightness"
    ],
    "dryness / dehydration+texture / rough skin": [
        "Deep hydration + dramatically smoother texture",
        "Plump, soft skin with reduced roughness",
        "Strong barrier + silky touch",
        "Even, comfortable surface"
    ],
    "acne / breakouts+dull skin": [
        "Clearer skin + brighter, healthier glow",
        "Fewer breakouts + reduced post-blemish marks",
        "Balanced oil + even tone",
        "Calmer complexion + visible radiance"
    ],
    "aging / fine lines+dryness / dehydration": [
        "Firmer skin + deep lasting hydration",
        "Reduced fine lines + plump, supple feel",
        "Improved elasticity + strong moisture barrier",
        "Youthful bounce + comfortable softness"
    ],
    # Fallback
    "default": [
        "Healthier, more balanced skin overall",
        "Visible improvement in your main concerns",
        "Stronger skin resilience & comfort",
        "Natural, confident glow from within"
    ]
}

def get_next_skin_goals(concerns):
    if not concerns:
        return NEXT_SKIN_GOALS["default"][:4]

    normalized = [c.lower().strip() for c in concerns]

    if len(normalized) == 1:
        key = normalized[0]
        return NEXT_SKIN_GOALS.get(key, NEXT_SKIN_GOALS["default"])[:5]

    normalized.sort(key=len, reverse=True)
    combo_key = "+".join(normalized[:2])
    if combo_key in NEXT_SKIN_GOALS:
        return NEXT_SKIN_GOALS[combo_key][:5]

    primary = normalized[0]
    goals = NEXT_SKIN_GOALS.get(primary, NEXT_SKIN_GOALS["default"])[:3]

    shared = [
        "Stronger, more resilient skin barrier",
        "Comfortable, confident daily feel",
        "Visible progress with consistency"
    ]
    goals.append(shared[0])

    return goals[:5]

# ────────────────────────────────────────────────
# Main form
# ────────────────────────────────────────────────
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

        # Button to progress page
        st.markdown("---")
        if st.button("I've started this routine → Track my progress & get follow-up advice"):
            st.switch_page("pages/1_Progress_Tracker.py")

        if area == "Face":
            st.markdown("---")
            want_body = st.radio("Would you like matching body products for your face concern?", ("No thanks", "Yes, show me"))
            if want_body == "Yes, show me":
                st.subheader("Matching Body Products")
                body_routine = build_routine(df, skin_type, concerns, is_sensitive_val, is_pregnant_val, using_prescription_val, "Body")
                for step, (details, _) in body_routine.items():
                    st.markdown(f"**{step}**  \n{details}")

        # ── Personalized goals ────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🌟 Your Next Skin Goals")

        goals = get_next_skin_goals(concerns)

        for goal in goals:
            st.markdown(f"• **{goal}**")

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

