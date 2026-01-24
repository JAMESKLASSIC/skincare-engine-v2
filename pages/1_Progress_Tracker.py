import streamlit as st

st.title("Track Your Skin Progress")

st.markdown("Tell us how your skin has responded so far — we'll give you personalized next steps.")

with st.form("progress_form"):
    st.subheader("Update your progress")

    time_used = st.selectbox(
        "How long have you been using your current routine?",
        ["Less than 2 weeks", "2–4 weeks", "4–8 weeks", "8+ weeks", "Not started yet"]
    )

    improvements = st.multiselect(
        "What has improved?",
        [
            "Less dryness/tightness",
            "More hydration/plumpness",
            "Smoother texture",
            "Brighter/radiant skin",
            "Fewer breakouts",
            "Less irritation/redness",
            "Nothing yet",
            "Other (please describe below)"
        ]
    )

    problems = st.multiselect(
        "What problems are you still having (or new issues)?",
        [
            "Still dry/tight",
            "Still dull",
            "Still rough texture",
            "Breakouts/purging",
            "Irritation/stinging",
            "No improvement",
            "Worse than before",
            "New sensitivity",
            "Other (please describe below)"
        ]
    )

    notes = st.text_area(
        "Extra notes (e.g. purging, how products feel, photos description, etc.)",
        height=120,
        placeholder="Example: My cheeks are less flaky but forehead still rough..."
    )

    submitted = st.form_submit_button("Submit Progress & Get Advice", type="primary")

if submitted:
    st.success("Progress submitted! Here's your follow-up advice:")

    if "Not started yet" in time_used:
        st.info("Great — start slowly: introduce **one product every 7–10 days**. Always patch test first!")
    elif "Less than 2 weeks" in time_used:
        st.info("It's still early! Most actives take **4–8 weeks** to show real results. Keep going consistently.")
    else:
        if problems:
            st.warning("Possible next steps:")
            if any(p in problems for p in ["Still dry/tight", "Still dull"]):
                st.write("• Layer a **hydrating essence or serum** before moisturizer")
                st.write("• Consider a **richer night cream** or **occlusive** to lock in moisture")
            if "Breakouts/purging" in problems:
                st.write("• Purging is normal with exfoliating actives — usually settles in **4–6 weeks**")
            if "Irritation/stinging" in problems or "New sensitivity" in problems:
                st.write("• Reduce frequency to **every other day**")
                st.write("• Add soothing ingredients: **centella**, **panthenol**, **ceramides**")
            if "Worse than before" in problems:
                st.error("**Stop new products immediately** and consult a dermatologist if irritation persists.")
        else:
            st.success("Looks like good progress! Keep the routine consistent for another **4–8 weeks**.")

        st.info("Want a full updated routine? Book a consultation or share progress photos next time.")

# Back button to main page
st.markdown("[← Back to generate a new routine](/ )")
