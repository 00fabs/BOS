import streamlit as st
import pandas as pd

# ── Page Config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Breakout Validity Validator",
    page_icon="📊",
    layout="centered"
)

# ── Math Engine ───────────────────────────────────────────────

def calc_sms(breakout_pips, atr_14_pips):
    if atr_14_pips == 0:
        return None, "ERROR: ATR cannot be zero"
    return round(abs(breakout_pips) / atr_14_pips, 4), "OK"


def calc_entry_bvs(sms, sms_min=1.0):
    if sms < sms_min:
        return round(sms, 4), "INVALID"
    return round(sms, 4), "VALID"


def calc_momentum_gap(eurx_mom, usdx_mom, min_gap=20.0):
    gap = abs(eurx_mom - usdx_mom)
    if gap < min_gap:
        return round(gap, 4), "WEAK"
    if eurx_mom > usdx_mom:
        return round(gap, 4), "BUY"
    elif usdx_mom > eurx_mom:
        return round(gap, 4), "SELL"
    return round(gap, 4), "NEUTRAL"


def check_alignment(direction, bias):
    if bias in ("WEAK", "NEUTRAL"):
        return "CAUTION"
    if direction == bias:
        return "CONFIRMED"
    return "CONFLICT"


def calc_icr(impulse_c, consol_c):
    if consol_c == 0:
        return None, "ERROR: Consolidation cannot be zero"
    icr = impulse_c / consol_c
    return round(-icr if icr < 1.0 else icr, 4), "OK"


def calc_full_bvs(sms, icr, sms_weight=0.6, icr_weight=0.4):
    if sms < 1.0:
        bvs = (sms * sms_weight) + (abs(icr) * icr_weight)
        return round(bvs, 4), "POOR"
    icr_contribution = (
        abs(icr) * icr_weight if icr < 0
        else min(abs(icr), 0.5) * icr_weight
    )
    bvs = (sms * sms_weight) + icr_contribution
    quality = "HIGH" if bvs >= 1.2 else "MEDIUM" if bvs >= 1.0 else "LOW"
    return round(bvs, 4), quality


# ── Session State ─────────────────────────────────────────────
if "entry_log" not in st.session_state:
    st.session_state.entry_log = []
if "review_log" not in st.session_state:
    st.session_state.review_log = []

# ── UI ────────────────────────────────────────────────────────
st.title("📊 Breakout Validity Validator")
st.caption("Quantitative breakout scoring — Entry Gate & Post-Trade Review")

tab1, tab2 = st.tabs(["🚦 Entry Gate", "📋 Post-Trade Review"])

# ════════════════════════════════════════════════════════════
# TAB 1 — ENTRY GATE
# ════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Entry Gate")
    st.caption(
        "Fill in at breakout candle close. "
        "Breakout pips = distance from range boundary to candle close. "
        "ATR = 14-period ATR on your timeframe."
    )

    with st.form("entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            pair      = st.text_input("Pair", value="EURUSD")
            direction = st.selectbox("Your Direction", ["BUY", "SELL"])
            breakout_pips = st.number_input(
                "Breakout Pips", min_value=0.0, value=18.0, step=0.1,
                help="Distance in pips from range boundary to breakout candle close"
            )
            atr_pips = st.number_input(
                "ATR (14) in Pips", min_value=0.0, value=10.0, step=0.1,
                help="14-period Average True Range on your trading timeframe"
            )
        with col2:
            consol_candles = st.number_input(
                "Consolidation Candles", min_value=1, value=7, step=1,
                help="Number of candles that formed the range before the breakout"
            )
            eurx_mom = st.number_input(
                "EURX Momentum", value=-43.09, step=0.01,
                help="Euro index momentum value"
            )
            usdx_mom = st.number_input(
                "USDX Momentum", value=33.33, step=0.01,
                help="Dollar index momentum value"
            )

        submitted = st.form_submit_button("▶ Validate Entry", use_container_width=True)

    if submitted:
        sms, err = calc_sms(breakout_pips, atr_pips)

        if sms is None:
            st.error(err)
        else:
            bvs, verdict   = calc_entry_bvs(sms)
            gap, bias      = calc_momentum_gap(eurx_mom, usdx_mom)
            alignment      = check_alignment(direction, bias)

            # ── Result Cards ──
            st.divider()
            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric("SMS", bvs)
                if verdict == "VALID":
                    st.success("✅ SMS VALID")
                else:
                    st.error("❌ SMS INVALID — noise break")

            with c2:
                bias_label = f"{bias} ({gap})"
                st.metric("Momentum Gap", round(gap, 2))
                if bias == "WEAK":
                    st.warning("⚠️ WEAK GAP")
                elif bias == "NEUTRAL":
                    st.warning("⚠️ NEUTRAL")
                else:
                    st.info(f"Bias: {bias}")

            with c3:
                st.metric("Direction", direction)
                if alignment == "CONFIRMED":
                    st.success("✅ CONFIRMED")
                elif alignment == "CONFLICT":
                    st.error("❌ CONFLICT")
                else:
                    st.warning("⚠️ CAUTION")

            # ── Final Verdict Banner ──
            st.divider()
            all_clear = verdict == "VALID" and alignment == "CONFIRMED"
            caution   = verdict == "VALID" and alignment == "CAUTION"

            if all_clear:
                st.success(f"### ✅ TAKE THE TRADE — {direction} {pair}")
            elif caution:
                st.warning(f"### ⚠️ PROCEED WITH CAUTION — {direction} {pair}  \nSMS valid but momentum gap is weak")
            elif verdict == "VALID" and alignment == "CONFLICT":
                st.error(f"### ❌ SKIP — Direction conflicts with momentum bias")
            else:
                st.error(f"### ❌ SKIP — Breakout did not clear ATR noise")

            # ── Log Entry ──
            st.session_state.entry_log.append({
                "Pair"        : pair,
                "Direction"   : direction,
                "Breakout(p)" : breakout_pips,
                "ATR(p)"      : atr_pips,
                "Consol(c)"   : consol_candles,
                "SMS"         : sms,
                "Entry BVS"   : bvs,
                "MOM Gap"     : gap,
                "Bias"        : bias,
                "Alignment"   : alignment,
                "Verdict"     : verdict,
            })

    # ── Session Log ──
    if st.session_state.entry_log:
        st.divider()
        st.subheader("Session Log")
        df = pd.DataFrame(st.session_state.entry_log)
        st.dataframe(df, use_container_width=True)
        if st.button("🗑 Clear Entry Log"):
            st.session_state.entry_log = []
            st.rerun()


# ════════════════════════════════════════════════════════════
# TAB 2 — POST-TRADE REVIEW
# ════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Post-Trade Review")
    st.caption(
        "Fill in after the trade closes. "
        "Impulse candles = number of candles the move drove before stalling. "
        "Consolidation candles = range candles counted at entry."
    )

    with st.form("review_form"):
        col1, col2 = st.columns(2)
        with col1:
            r_pair         = st.text_input("Pair", value="EURUSD", key="r_pair")
            r_direction    = st.selectbox("Direction Taken", ["BUY", "SELL"], key="r_dir")
            r_result       = st.selectbox("Trade Result", ["WIN", "LOSS", "BREAKEVEN"], key="r_result")
            r_breakout_p   = st.number_input(
                "Breakout Pips", min_value=0.0, value=18.0, step=0.1, key="r_bp"
            )
        with col2:
            r_atr          = st.number_input(
                "ATR (14) in Pips", min_value=0.0, value=10.0, step=0.1, key="r_atr"
            )
            r_impulse_c    = st.number_input(
                "Impulse Candles", min_value=1, value=3, step=1, key="r_ic",
                help="How many candles did the move drive after your entry before stalling"
            )
            r_consol_c     = st.number_input(
                "Consolidation Candles", min_value=1, value=7, step=1, key="r_cc",
                help="Range candles — same value you counted at entry"
            )

        r_submitted = st.form_submit_button("▶ Score Trade", use_container_width=True)

    if r_submitted:
        sms, err = calc_sms(r_breakout_p, r_atr)

        if sms is None:
            st.error(err)
        else:
            icr, icr_err = calc_icr(r_impulse_c, r_consol_c)

            if icr is None:
                st.error(icr_err)
            else:
                full_bvs, quality = calc_full_bvs(sms, icr)

                st.divider()
                c1, c2, c3 = st.columns(3)

                with c1:
                    st.metric("SMS", sms)
                with c2:
                    st.metric("ICR", icr)
                    urgency = "Fast / Urgent" if icr < 0 else "Slow Grind"
                    st.caption(urgency)
                with c3:
                    st.metric("Full BVS", full_bvs)

                st.divider()
                color_map = {
                    "HIGH" : st.success,
                    "MEDIUM": st.warning,
                    "LOW"  : st.warning,
                    "POOR" : st.error,
                }
                result_emoji = {"WIN": "🟢", "LOSS": "🔴", "BREAKEVEN": "🟡"}
                color_map[quality](
                    f"### {result_emoji[r_result]} {r_result} — "
                    f"TRADE QUALITY: {quality}  \n"
                    f"Full BVS: {full_bvs}"
                )

                st.session_state.review_log.append({
                    "Pair"      : r_pair,
                    "Direction" : r_direction,
                    "Result"    : r_result,
                    "SMS"       : sms,
                    "ICR"       : icr,
                    "Full BVS"  : full_bvs,
                    "Quality"   : quality,
                })

    if st.session_state.review_log:
        st.divider()
        st.subheader("Review Log")
        df2 = pd.DataFrame(st.session_state.review_log)
        st.dataframe(df2, use_container_width=True)
        if st.button("🗑 Clear Review Log"):
            st.session_state.review_log = []
            st.rerun()
