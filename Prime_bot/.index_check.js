
  marked.setOptions({ breaks: true, gfm: true });

  /* ── UI translations ── */
  var UI = {
    en: {
      title: "Prime Bank Assistant", subtitle: "Credit Card Help & Guidance",
      placeholder: "Ask about credit cards, eligibility, fees...",
      hint: 'Press <kbd style="font-family:var(--font-mono);font-size:10px;background:#f0f0f0;padding:1px 4px;border-radius:3px;border:1px solid #ddd;">Enter</kbd> to send \xB7 <kbd style="font-family:var(--font-mono);font-size:10px;background:#f0f0f0;padding:1px 4px;border-radius:3px;border:1px solid #ddd;">Shift+Enter</kbd> for new line',
      newChat: "New chat", thinking: "Thinking",
      moreDetails: "More details",
      sourceCurrent: "Based on current card details",
      sourceVaries: "Some details may vary by card type",
      sourceService: "Based on current service information",
      sourceEligibility: "Based on your current details and card rules",
      welcomeTitle: "How can I help you today?",
      welcomeDesc: "I can help you find the right Prime Bank credit card, check your eligibility, compare products, or assist with your existing card.",
      chips: [
        { label: "What cards do you offer?",  msg: "What credit cards does Prime Bank offer?" },
        { label: "Halal / Islamic card",       msg: "I need a halal credit card" },
        { label: "Check my eligibility",       msg: "Am I eligible for a credit card?" },
        { label: "Compare cards",              msg: "Compare Visa Gold and Visa Platinum" },
        { label: "How to apply",               msg: "How do I apply for a credit card?" },
        { label: "Lost card help",             msg: "I lost my card, what should I do?" },
      ],
      langBtn: "\u09AC\u09BE\u0982",
    },
    bn: {
      title: "\u09AA\u09CD\u09B0\u09BE\u0987\u09AE \u09AC\u09CD\u09AF\u09BE\u0982\u0995 \u09B8\u09B9\u0995\u09BE\u09B0\u09C0",
      subtitle: "\u0995\u09CD\u09B0\u09C7\u09A1\u09BF\u099F \u0995\u09BE\u09B0\u09CD\u09A1 \u09B8\u09BE\u09B9\u09BE\u09AF\u09CD\u09AF \u0993 \u0997\u09BE\u0987\u09A1\u09C7\u09A8\u09CD\u09B8",
      placeholder: "\u0995\u09CD\u09B0\u09C7\u09A1\u09BF\u099F \u0995\u09BE\u09B0\u09CD\u09A1, \u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE, \u09AB\u09BF \u09B8\u09AE\u09CD\u09AA\u09B0\u09CD\u0995\u09C7 \u099C\u09BF\u099C\u09CD\u099E\u09C7\u09B8 \u0995\u09B0\u09C1\u09A8...",
      hint: '\u09AA\u09BE\u09A0\u09BE\u09A4\u09C7 <kbd style="font-family:var(--font-mono);font-size:10px;background:#f0f0f0;padding:1px 4px;border-radius:3px;border:1px solid #ddd;">Enter</kbd> \xB7 \u09A8\u09A4\u09C1\u09A8 \u09B2\u09BE\u0987\u09A8\u09C7\u09B0 \u099C\u09A8\u09CD\u09AF <kbd style="font-family:var(--font-mono);font-size:10px;background:#f0f0f0;padding:1px 4px;border-radius:3px;border:1px solid #ddd;">Shift+Enter</kbd>',
      newChat: "\u09A8\u09A4\u09C1\u09A8 \u099A\u09CD\u09AF\u09BE\u099F", thinking: "\u09AD\u09BE\u09AC\u099B\u09BF",
      moreDetails: "\u0986\u09B0\u0993 \u09AC\u09BF\u09B8\u09CD\u09A4\u09BE\u09B0\u09BF\u09A4",
      sourceCurrent: "\u09AC\u09B0\u09CD\u09A4\u09AE\u09BE\u09A8 \u0995\u09BE\u09B0\u09CD\u09A1 \u09A4\u09A5\u09CD\u09AF\u09C7\u09B0 \u09AD\u09BF\u09A4\u09CD\u09A4\u09BF\u09A4\u09C7",
      sourceVaries: "\u0995\u09BF\u099B\u09C1 \u09A4\u09A5\u09CD\u09AF \u0995\u09BE\u09B0\u09CD\u09A1\u09AD\u09C7\u09A6\u09C7 \u09AD\u09BF\u09A8\u09CD\u09A8 \u09B9\u09A4\u09C7 \u09AA\u09BE\u09B0\u09C7",
      sourceService: "\u09AC\u09B0\u09CD\u09A4\u09AE\u09BE\u09A8 \u09B8\u09BE\u09B0\u09CD\u09AD\u09BF\u09B8 \u09A4\u09A5\u09CD\u09AF\u09C7\u09B0 \u09AD\u09BF\u09A4\u09CD\u09A4\u09BF\u09A4\u09C7",
      sourceEligibility: "\u0986\u09AA\u09A8\u09BE\u09B0 \u09A4\u09A5\u09CD\u09AF \u0993 \u0995\u09BE\u09B0\u09CD\u09A1 \u09A8\u09C0\u09A4\u09BF\u09B0 \u09AD\u09BF\u09A4\u09CD\u09A4\u09BF\u09A4\u09C7",
      welcomeTitle: "\u0986\u099C \u0995\u09C0\u09AD\u09BE\u09AC\u09C7 \u09B8\u09BE\u09B9\u09BE\u09AF\u09CD\u09AF \u0995\u09B0\u09A4\u09C7 \u09AA\u09BE\u09B0\u09BF?",
      welcomeDesc: "\u0986\u09AE\u09BF \u0986\u09AA\u09A8\u09BE\u0995\u09C7 \u09B8\u09A0\u09BF\u0995 \u09AA\u09CD\u09B0\u09BE\u0987\u09AE \u09AC\u09CD\u09AF\u09BE\u0982\u0995 \u0995\u09CD\u09B0\u09C7\u09A1\u09BF\u099F \u0995\u09BE\u09B0\u09CD\u09A1 \u0996\u09C1\u0981\u099C\u09C7 \u09AA\u09C7\u09A4\u09C7, \u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u09AF\u09BE\u099A\u09BE\u0987 \u0995\u09B0\u09A4\u09C7, \u09AA\u09A3\u09CD\u09AF \u09A4\u09C1\u09B2\u09A8\u09BE \u0995\u09B0\u09A4\u09C7 \u09AC\u09BE \u09AC\u09BF\u09A6\u09CD\u09AF\u09AE\u09BE\u09A8 \u0995\u09BE\u09B0\u09CD\u09A1\u09C7 \u09B8\u09BE\u09B9\u09BE\u09AF\u09CD\u09AF \u0995\u09B0\u09A4\u09C7 \u09AA\u09BE\u09B0\u09BF\u0964",
      chips: [
        { label: "\u0995\u09C0 \u0995\u09BE\u09B0\u09CD\u09A1 \u0986\u099B\u09C7?",           msg: "\u09AA\u09CD\u09B0\u09BE\u0987\u09AE \u09AC\u09CD\u09AF\u09BE\u0982\u0995 \u0995\u09C0 \u0995\u09C0 \u0995\u09CD\u09B0\u09C7\u09A1\u09BF\u099F \u0995\u09BE\u09B0\u09CD\u09A1 \u0985\u09AB\u09BE\u09B0 \u0995\u09B0\u09C7?" },
        { label: "\u09B9\u09BE\u09B2\u09BE\u09B2 / \u0987\u09B8\u09B2\u09BE\u09AE\u09BF\u0995 \u0995\u09BE\u09B0\u09CD\u09A1",   msg: "\u0986\u09AE\u09BE\u09B0 \u098F\u0995\u099F\u09BF \u09B9\u09BE\u09B2\u09BE\u09B2 \u0995\u09CD\u09B0\u09C7\u09A1\u09BF\u099F \u0995\u09BE\u09B0\u09CD\u09A1 \u09A6\u09B0\u0995\u09BE\u09B0" },
        { label: "\u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u09AF\u09BE\u099A\u09BE\u0987 \u0995\u09B0\u09C1\u09A8",       msg: "\u0986\u09AE\u09BF \u0995\u09BF \u0995\u09CD\u09B0\u09C7\u09A1\u09BF\u099F \u0995\u09BE\u09B0\u09CD\u09A1\u09C7\u09B0 \u099C\u09A8\u09CD\u09AF \u09AF\u09CB\u0997\u09CD\u09AF?" },
        { label: "\u0995\u09BE\u09B0\u09CD\u09A1 \u09A4\u09C1\u09B2\u09A8\u09BE \u0995\u09B0\u09C1\u09A8",          msg: "\u09AD\u09BF\u09B8\u09BE \u0997\u09CB\u09B2\u09CD\u09A1 \u098F\u09AC\u0982 \u09AD\u09BF\u09B8\u09BE \u09AA\u09CD\u09B2\u09BE\u099F\u09BF\u09A8\u09BE\u09AE \u09A4\u09C1\u09B2\u09A8\u09BE \u0995\u09B0\u09C1\u09A8" },
        { label: "\u0986\u09AC\u09C7\u09A6\u09A8 \u0995\u09B0\u09AC\u09C7\u09A8 \u0995\u09C0\u09AD\u09BE\u09AC\u09C7",       msg: "\u0995\u09CD\u09B0\u09C7\u09A1\u09BF\u099F \u0995\u09BE\u09B0\u09CD\u09A1\u09C7\u09B0 \u099C\u09A8\u09CD\u09AF \u0986\u09AC\u09C7\u09A6\u09A8 \u0995\u09B0\u09AC \u0995\u09C0\u09AD\u09BE\u09AC\u09C7?" },
        { label: "\u0995\u09BE\u09B0\u09CD\u09A1 \u09B9\u09BE\u09B0\u09BF\u09AF\u09BC\u09C7\u099B\u09BF",           msg: "\u0986\u09AE\u09BE\u09B0 \u0995\u09BE\u09B0\u09CD\u09A1 \u09B9\u09BE\u09B0\u09BF\u09AF\u09BC\u09C7 \u0997\u09C7\u099B\u09C7, \u0995\u09C0 \u0995\u09B0\u09AC?" },
      ],
      langBtn: "EN",
    },
  };

  var FOLLOWUP = {
    en: {
      eligible:             ["How do I apply?", "What documents do I need?", "Compare with another card"],
      ineligible:           ["Show me other options", "What are the income requirements?", "How to improve eligibility?"],
      borderline:           ["Show easier-to-get cards", "What's the minimum income?", "Tips to strengthen application"],
      comparison:           ["Check my eligibility", "How to apply?", "Explain the fees"],
      product_details:      ["Check my eligibility", "Compare cards", "How to apply?"],
      how_to_apply:         ["Check eligibility first", "What are the fees?", "How long does approval take?"],
      existing_cardholder:  ["Get a replacement card", "How do I check my transactions?", "How do I change my PIN?"],
      i_need_a_credit_card: ["Check my eligibility", "Compare cards", "How to apply?"],
      catalog_query:        ["Conventional cards", "Islamic / Halal cards", "Check my eligibility"],
      discovery:            ["Conventional please", "Islamic / Halal please", "Tell me more"],
      general:              ["What cards are available?", "Check my eligibility", "Compare cards"],
    },
    bn: {
      eligible:             ["\u0986\u09AC\u09C7\u09A6\u09A8 \u0995\u09B0\u09AC \u0995\u09C0\u09AD\u09BE\u09AC\u09C7?", "\u0995\u09C0 \u0995\u09C0 \u0995\u09BE\u0997\u099C\u09AA\u09A4\u09CD\u09B0 \u09B2\u09BE\u0997\u09AC\u09C7?", "\u0985\u09A8\u09CD\u09AF \u0995\u09BE\u09B0\u09CD\u09A1\u09C7\u09B0 \u09B8\u09BE\u09A5\u09C7 \u09A4\u09C1\u09B2\u09A8\u09BE"],
      ineligible:           ["\u0985\u09A8\u09CD\u09AF \u0985\u09AA\u09B6\u09A8 \u09A6\u09C7\u0996\u09BE\u09A8", "\u0986\u09AF\u09BC\u09C7\u09B0 \u09AA\u09CD\u09B0\u09AF\u09BC\u09CB\u099C\u09A8\u09C0\u09AF\u09BC\u09A4\u09BE \u0995\u09C0?", "\u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u0989\u09A8\u09CD\u09A8\u09A4 \u0995\u09B0\u09AC \u0995\u09C0\u09AD\u09BE\u09AC\u09C7?"],
      borderline:           ["\u09B8\u09B9\u099C\u09C7 \u09AA\u09BE\u0993\u09AF\u09BC\u09BE \u09AF\u09BE\u09AF\u09BC \u098F\u09AE\u09A8 \u0995\u09BE\u09B0\u09CD\u09A1", "\u09A8\u09CD\u09AF\u09C2\u09A8\u09A4\u09AE \u0986\u09AF\u09BC \u0995\u09A4?", "\u0986\u09AC\u09C7\u09A6\u09A8 \u09B6\u0995\u09CD\u09A4\u09BF\u09B6\u09BE\u09B2\u09C0 \u0995\u09B0\u09BE\u09B0 \u099F\u09BF\u09AA\u09B8"],
      comparison:           ["\u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u09AF\u09BE\u099A\u09BE\u0987 \u0995\u09B0\u09C1\u09A8", "\u0986\u09AC\u09C7\u09A6\u09A8 \u0995\u09B0\u09AC \u0995\u09C0\u09AD\u09BE\u09AC\u09C7?", "\u09AB\u09BF \u09B8\u09AE\u09CD\u09AA\u09B0\u09CD\u0995\u09C7 \u099C\u09BE\u09A8\u09C1\u09A8"],
      product_details:      ["\u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u09AF\u09BE\u099A\u09BE\u0987 \u0995\u09B0\u09C1\u09A8", "\u0995\u09BE\u09B0\u09CD\u09A1 \u09A4\u09C1\u09B2\u09A8\u09BE \u0995\u09B0\u09C1\u09A8", "\u0986\u09AC\u09C7\u09A6\u09A8 \u0995\u09B0\u09AC \u0995\u09C0\u09AD\u09BE\u09AC\u09C7?"],
      how_to_apply:         ["\u0986\u0997\u09C7 \u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u09AF\u09BE\u099A\u09BE\u0987 \u0995\u09B0\u09C1\u09A8", "\u09AB\u09BF \u0995\u09A4?", "\u0985\u09A8\u09C1\u09AE\u09CB\u09A6\u09A8 \u09AA\u09C7\u09A4\u09C7 \u0995\u09A4\u09A6\u09BF\u09A8 \u09B2\u09BE\u0997\u09C7?"],
      existing_cardholder:  ["\u09A8\u09A4\u09C1\u09A8 \u0995\u09BE\u09B0\u09CD\u09A1 \u09AA\u09BE\u09AC \u0995\u09C0\u09AD\u09BE\u09AC\u09C7?", "\u09B2\u09C7\u09A8\u09A6\u09C7\u09A8 \u0987\u09A4\u09BF\u09B9\u09BE\u09B8 \u0995\u09C0\u09AD\u09BE\u09AC\u09C7 \u09A6\u09C7\u0996\u09AC?", "\u09AA\u09BF\u09A8 \u09AA\u09B0\u09BF\u09AC\u09B0\u09CD\u09A4\u09A8 \u0995\u09B0\u09AC \u0995\u09C0\u09AD\u09BE\u09AC\u09C7?"],
      i_need_a_credit_card: ["\u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u09AF\u09BE\u099A\u09BE\u0987 \u0995\u09B0\u09C1\u09A8", "\u0995\u09BE\u09B0\u09CD\u09A1 \u09A4\u09C1\u09B2\u09A8\u09BE \u0995\u09B0\u09C1\u09A8", "\u0986\u09AC\u09C7\u09A6\u09A8 \u0995\u09B0\u09AC \u0995\u09C0\u09AD\u09BE\u09AC\u09C7?"],
      catalog_query:        ["\u09AA\u09CD\u09B0\u099A\u09B2\u09BF\u09A4 \u09AC\u09CD\u09AF\u09BE\u0982\u0995\u09BF\u0982 \u0995\u09BE\u09B0\u09CD\u09A1", "\u0987\u09B8\u09B2\u09BE\u09AE\u09BF\u0995 / \u09B9\u09BE\u09B2\u09BE\u09B2 \u0995\u09BE\u09B0\u09CD\u09A1", "\u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u09AF\u09BE\u099A\u09BE\u0987 \u0995\u09B0\u09C1\u09A8"],
      discovery:            ["\u09AA\u09CD\u09B0\u099A\u09B2\u09BF\u09A4 \u09AC\u09CD\u09AF\u09BE\u0982\u0995\u09BF\u0982", "\u0987\u09B8\u09B2\u09BE\u09AE\u09BF\u0995 / \u09B9\u09BE\u09B2\u09BE\u09B2", "\u09AA\u09BE\u09B0\u09CD\u09A5\u0995\u09CD\u09AF \u09B8\u09AE\u09CD\u09AA\u09B0\u09CD\u0995\u09C7 \u0986\u09B0\u09CB \u099C\u09BE\u09A8\u09C1\u09A8"],
      general:              ["\u0995\u09C0 \u0995\u09BE\u09B0\u09CD\u09A1 \u0986\u099B\u09C7?", "\u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u09AF\u09BE\u099A\u09BE\u0987 \u0995\u09B0\u09C1\u09A8", "\u0995\u09BE\u09B0\u09CD\u09A1 \u09A4\u09C1\u09B2\u09A8\u09BE \u0995\u09B0\u09C1\u09A8"],
    },
  };

  /* ── State ── */
  var lang = "en", isBengali = false;
  var sessionId = null, isLoading = false;
  var ws = null, wsReady = false, reconnectDelay = 1000;
  var reconnectTimer = null, pingInterval = null;
  var activeBubble = null, activeThinkId = null, fullText = "";
  var activeFormId = null, thinkTimer = null, thinkStart = 0;
  var streamQueue = "", streamFlushTimer = null, lastDoneMeta = null;
  var emiTenure = 12;
  var activeEMICalcConfig = null;
  var activeEMICardIndex = 0;

  /* ── DOM refs ── */
  var messagesEl = document.getElementById("messages");
  var welcomeEl  = document.getElementById("welcome");
  var inputEl    = document.getElementById("inputBox");
  var sendBtnEl  = document.getElementById("sendBtn");
  var statusDot  = document.getElementById("statusDot");
  var statusText = document.getElementById("statusText");
  var scrollFab  = document.getElementById("scrollFab");
  var langBtn    = document.getElementById("langBtn");
  var btnClear   = document.getElementById("btnClear");

  /* ── Language ── */
  function applyUI() {
    var t = UI[lang];
    document.getElementById("hdrTitle").textContent     = t.title;
    document.getElementById("hdrSub").textContent       = t.subtitle;
    document.getElementById("welcomeTitle").textContent = t.welcomeTitle;
    document.getElementById("welcomeDesc").textContent  = t.welcomeDesc;
    document.getElementById("inputHint").innerHTML      = t.hint;
    inputEl.placeholder  = lastDoneMeta ? contextualPlaceholder(lastDoneMeta) : t.placeholder;
    langBtn.textContent  = t.langBtn;
    btnClear.textContent = t.newChat;
    renderWelcomeChips();
  }

  function renderWelcomeChips() {
    var el = document.getElementById("welcomeChips");
    el.innerHTML = "";
    UI[lang].chips.forEach(function(c) {
      var btn = document.createElement("button");
      btn.className = "suggestion-chip";
      btn.textContent = c.label;
      btn.onclick = function() { sendSuggestion(c.msg); };
      el.appendChild(btn);
    });
  }

  function toggleLanguage() {
    isBengali = !isBengali;
    lang = isBengali ? "bn" : "en";
    langBtn.classList.toggle("active", isBengali);
    applyUI();
  }

  function getBengaliSuffix() {
    return isBengali ? "\n\n\u0985\u09A8\u09C1\u0997\u09CD\u09B0\u09B9 \u0995\u09B0\u09C7 \u09AC\u09BE\u0982\u09B2\u09BE\u09AF\u09BC \u0989\u09A4\u09CD\u09A4\u09B0 \u09A6\u09BF\u09A8\u0964" : "";
  }

  function followupText(key) {
    var labels = {
      en: {
        eligibility: "Check my eligibility",
        apply: "How to apply?",
        compare: "Compare with another card",
        compareTwo: "Compare 2 only",
        feesOnly: "Show fees only",
        loungeBest: "Best for lounge access",
        whyCard: "Why this card?",
        alternatives: "Show alternatives",
        docs: "What documents are needed?",
        serviceHelp: "Show service steps",
        contact: "Contact center details",
        dispute: "How does dispute handling work?",
        emiExample: "Show example calculation",
        emiCharges: "Explain charges",
        cardDetails: "Show card details",
      },
      bn: {
        eligibility: "\u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE \u09AF\u09BE\u099A\u09BE\u0987 \u0995\u09B0\u09C1\u09A8",
        apply: "\u0986\u09AC\u09C7\u09A6\u09A8 \u0995\u09B0\u09AC \u0995\u09C0\u09AD\u09BE\u09AC\u09C7?",
        compare: "\u0985\u09A8\u09CD\u09AF \u0995\u09BE\u09B0\u09CD\u09A1\u09C7\u09B0 \u09B8\u09BE\u09A5\u09C7 \u09A4\u09C1\u09B2\u09A8\u09BE",
        compareTwo: "\u09B6\u09C1\u09A7\u09C1 \u09E8\u099F\u09BF \u0995\u09BE\u09B0\u09CD\u09A1 \u09A4\u09C1\u09B2\u09A8\u09BE",
        feesOnly: "\u09B6\u09C1\u09A7\u09C1 \u09AB\u09BF \u09A6\u09C7\u0996\u09BE\u09A8",
        loungeBest: "\u09B2\u09BE\u0989\u099E\u09CD\u099C \u09A6\u09BF\u0995 \u09A6\u09BF\u09AF\u09BC\u09C7 \u09B8\u09C7\u09B0\u09BE",
        whyCard: "\u098F\u0987 \u0995\u09BE\u09B0\u09CD\u09A1 \u0995\u09C7\u09A8?",
        alternatives: "\u0985\u09A8\u09CD\u09AF \u0993\u09AA\u09B6\u09A8 \u09A6\u09C7\u0996\u09BE\u09A8",
        docs: "\u0995\u09C0 \u0995\u09BE\u0997\u099C\u09AA\u09A4\u09CD\u09B0 \u09B2\u09BE\u0997\u09AC\u09C7?",
        serviceHelp: "\u09B8\u09BE\u09B0\u09CD\u09AD\u09BF\u09B8 \u09B8\u09CD\u099F\u09C7\u09AA \u09A6\u09C7\u0996\u09BE\u09A8",
        contact: "\u0995\u09A8\u099F\u09BE\u0995\u09CD\u099F \u09B8\u09C7\u09A8\u09CD\u099F\u09BE\u09B0 \u09A4\u09A5\u09CD\u09AF",
        dispute: "\u09A1\u09BF\u09B8\u09AA\u09BF\u0989\u099F \u09AA\u09CD\u09B0\u0995\u09CD\u09B0\u09BF\u09AF\u09BC\u09BE \u0995\u09C0?",
        emiExample: "\u0989\u09A6\u09BE\u09B9\u09B0\u09A3 \u09B9\u09BF\u09B8\u09BE\u09AC \u09A6\u09C7\u0996\u09BE\u09A8",
        emiCharges: "\u099A\u09BE\u09B0\u09CD\u099C \u09AC\u09CD\u09AF\u09BE\u0996\u09CD\u09AF\u09BE \u0995\u09B0\u09C1\u09A8",
        cardDetails: "\u0995\u09BE\u09B0\u09CD\u09A1\u09C7\u09B0 \u09A4\u09A5\u09CD\u09AF \u09A6\u09C7\u0996\u09BE\u09A8",
      }
    };
    return (labels[lang] && labels[lang][key]) || (labels.en && labels.en[key]) || key;
  }

  function intentLabel(intent) {
    var labels = {
      comparison: { en: "Comparison", bn: "\u09A4\u09C1\u09B2\u09A8\u09BE" },
      product_details: { en: "Card details", bn: "\u0995\u09BE\u09B0\u09CD\u09A1 \u09A4\u09A5\u09CD\u09AF" },
      how_to_apply: { en: "Application", bn: "\u0986\u09AC\u09C7\u09A6\u09A8" },
      existing_cardholder: { en: "Cardholder service", bn: "\u0995\u09BE\u09B0\u09CD\u09A1\u09B9\u09CB\u09B2\u09CD\u09A1\u09BE\u09B0 \u09B8\u09BE\u09B0\u09CD\u09AD\u09BF\u09B8" },
      i_need_a_credit_card: { en: "Recommendation", bn: "\u09B0\u09C7\u0995\u09AE\u09C7\u09A8\u09CD\u09A1\u09C7\u09B6\u09A8" },
      catalog_query: { en: "Card catalog", bn: "\u0995\u09BE\u09B0\u09CD\u09A1 \u0995\u09CD\u09AF\u09BE\u099F\u09BE\u09B2\u0997" },
      eligibility_check: { en: "Eligibility", bn: "\u09AF\u09CB\u0997\u09CD\u09AF\u09A4\u09BE" },
    };
    var label = labels[intent];
    return label ? label[lang] : (lang === "bn" ? "\u09AA\u09CD\u09B0\u09A4\u09BF\u0995\u09CD\u09B0\u09BF\u09AF\u09BC\u09BE" : "Response");
  }

  function sourceConfidenceText(meta) {
    var t = UI[lang];
    if (!meta || !meta.intent) return t.sourceCurrent;
    if (meta.intent === "existing_cardholder" || meta.intent === "how_to_apply") return t.sourceService;
    if (meta.intent === "eligibility_check") return t.sourceEligibility;
    if ((meta.cards || []).length > 1 || meta.banking_type === "both") return t.sourceVaries;
    return t.sourceCurrent;
  }

  function buildFollowupActions(meta) {
    var cards = (meta && meta.cards) || [];
    var actions = [];
    if (!meta) return [followupText("cardDetails"), followupText("eligibility"), followupText("compare")];

    if (meta.calculator === "emi") {
      actions.push(followupText("emiExample"), followupText("emiCharges"), followupText("eligibility"));
      return actions;
    }

    if (meta.intent === "comparison") {
      actions.push(followupText("feesOnly"), followupText("loungeBest"));
      if (cards.length > 2) actions.push(followupText("compareTwo"));
      else actions.push(followupText("eligibility"));
      return actions;
    }

    if (meta.intent === "product_details" || meta.intent === "i_need_a_credit_card" || meta.intent === "catalog_query") {
      actions.push(followupText("whyCard"), followupText("alternatives"), followupText("eligibility"));
      return actions;
    }

    if (meta.intent === "how_to_apply") {
      actions.push(followupText("docs"), followupText("feesOnly"), followupText("eligibility"));
      return actions;
    }

    if (meta.intent === "existing_cardholder") {
      actions.push(followupText("serviceHelp"), followupText("dispute"), followupText("contact"));
      return actions;
    }

    actions.push(followupText("cardDetails"), followupText("eligibility"), followupText("compare"));
    return actions;
  }

  function contextualPlaceholder(meta) {
    if (!meta) return UI[lang].placeholder;
    if (meta.intent === "comparison") return lang === "bn" ? "\u098F\u0996\u09A8 \u09AC\u09B2\u09C1\u09A8: \u09AB\u09BF \u09A6\u09BF\u0995 \u09A6\u09BF\u09AF\u09BC\u09C7 \u09A4\u09C1\u09B2\u09A8\u09BE \u0995\u09B0\u09C1\u09A8..." : "Now ask something like: compare fees only or best for lounge access...";
    if (meta.intent === "eligibility_check") return lang === "bn" ? "\u098F\u0996\u09A8 \u09AC\u09B2\u09C1\u09A8: \u0995\u09C0 \u0995\u09BE\u0997\u099C\u09AA\u09A4\u09CD\u09B0 \u09B2\u09BE\u0997\u09AC\u09C7..." : "Now ask something like: what documents are needed...";
    if (meta.intent === "existing_cardholder") return lang === "bn" ? "\u098F\u0996\u09A8 \u09AC\u09B2\u09C1\u09A8: \u09B2\u09B8\u09CD\u099F \u0995\u09BE\u09B0\u09CD\u09A1, \u09A1\u09BF\u09B8\u09AA\u09BF\u0989\u099F, \u0995\u09A8\u099F\u09BE\u0995\u09CD\u099F \u09B8\u09C7\u09A8\u09CD\u099F\u09BE\u09B0..." : "Now ask something like: lost card, dispute, or contact center...";
    if (meta.intent === "product_details" && (meta.cards || []).length === 1) return lang === "bn" ? "\u098F\u0996\u09A8 \u09AC\u09B2\u09C1\u09A8: \u098F\u099F\u09BF \u0985\u09A8\u09CD\u09AF \u0995\u09BE\u09B0\u09CD\u09A1\u09C7\u09B0 \u09B8\u09BE\u09A5\u09C7 \u09A4\u09C1\u09B2\u09A8\u09BE \u0995\u09B0\u09C1\u09A8..." : "Now ask something like: compare this with another card...";
    return UI[lang].placeholder;
  }

  /* ── WebSocket ── */
  function wsUrl() {
    var proto = location.protocol === "https:" ? "wss" : "ws";
    return proto + "://" + location.host + "/ws/chat";
  }

  function connect() {
    if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) return;
    setStatus("connecting");
    ws = new WebSocket(wsUrl());
    ws.onopen = function() {
      wsReady = true; reconnectDelay = 1000;
      setStatus("online"); setInputEnabled(true); inputEl.focus();
      pingInterval = setInterval(function() {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }));
      }, 25000);
    };
    ws.onmessage = function(evt) {
      var data; try { data = JSON.parse(evt.data); } catch(e) { return; }
      handleServerMessage(data);
    };
    ws.onclose = function() {
      wsReady = false; clearInterval(pingInterval);
      setStatus("offline"); setInputEnabled(false);
      if (isLoading) finishLoading();
      reconnectTimer = setTimeout(function() {
        reconnectDelay = Math.min(reconnectDelay * 2, 16000); connect();
      }, reconnectDelay);
    };
    ws.onerror = function() { ws.close(); };
  }

  function handleServerMessage(data) {
    switch (data.type) {
      case "session_id": sessionId = data.session_id; break;
      case "show_preference_form":
        if (activeThinkId) { removeThinking(activeThinkId); activeThinkId = null; }
        activeBubble = null; fullText = ""; streamQueue = "";
        renderPreferenceForm(data.schema); finishLoading(); break;
      case "show_eligibility_form":
        if (activeThinkId) { removeThinking(activeThinkId); activeThinkId = null; }
        activeBubble = null; fullText = ""; streamQueue = "";
        renderEligibilityForm(data.schema); finishLoading(); break;
      case "eligibility_verdicts":
        if (activeThinkId) { removeThinking(activeThinkId); activeThinkId = null; }
        activeBubble = null; fullText = ""; streamQueue = "";
        appendEligibilityVerdicts(data);
        break;
      case "progress":
        if (!activeThinkId) { activeThinkId = showThinking(); }
        updateThinkingProgress(activeThinkId, data.message || "Preparing answer", data.stage || "");
        scrollToBottom(); break;
      case "token":
        if (!activeBubble) {
          if (activeThinkId) { removeThinking(activeThinkId); activeThinkId = null; }
          activeBubble = createBotBubble(); fullText = "";
        }
        fullText += data.token;
        queueStreamRender(activeBubble, data.token);
        scrollToBottom(); break;
      case "done":
        if (activeBubble) {
          flushStreamQueue(activeBubble, true);
          lastDoneMeta = data;
          renderBotBubble(activeBubble, fullText, data);
          appendFollowupChips(data);
          inputEl.placeholder = contextualPlaceholder(data);
          if (data.calculator === "emi") createEMICalcBubble(data.calculator_config);
          else if (data.calculator === "rewards") createRewardsCalcBubble();
        }
        activeBubble = null; fullText = ""; streamQueue = ""; finishLoading(); break;
      case "cleared": sessionId = null; break;
      case "error":
        if (activeThinkId) { removeThinking(activeThinkId); activeThinkId = null; }
        activeBubble = null; fullText = ""; streamQueue = "";
        appendBotBubble("Sorry, something went wrong. Please try again or call **16218**.");
        finishLoading(); break;
      case "pong": break;
    }
  }

  function queueStreamRender(bubble, token) {
    streamQueue += token || "";
    if (streamFlushTimer) return;
    streamFlushTimer = setTimeout(function() {
      flushStreamQueue(bubble, false);
    }, 48);
  }

  function flushStreamQueue(bubble, force) {
    if (streamFlushTimer) {
      clearTimeout(streamFlushTimer);
      streamFlushTimer = null;
    }
    if (!bubble) return;
    if (!streamQueue && !force) return;
    renderStreamingBubble(bubble, fullText);
    streamQueue = "";
  }

  /* ── Message helpers ── */
  function nowTime() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function appendTimestamp(group, isUser) {
    var meta = document.createElement("div"); meta.className = "msg-meta";
    var span = document.createElement("span"); span.className = "msg-time";
    span.textContent = nowTime(); meta.appendChild(span); group.appendChild(meta);
  }

  function makeCopyBtn(bubbleEl) {
    var btn = document.createElement("button");
    btn.className = "copy-btn"; btn.title = "Copy";
    btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>';
    btn.onclick = function(e) {
      e.stopPropagation();
      var text = bubbleEl.innerText || "";
      navigator.clipboard.writeText(text).then(function() {
        btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>';
        btn.classList.add("copied");
        setTimeout(function() {
          btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>';
          btn.classList.remove("copied");
        }, 1500);
      }).catch(function() {});
    };
    return btn;
  }

  function createBotBubble() {
    var group  = document.createElement("div"); group.className  = "msg-group";
    var row    = document.createElement("div"); row.className    = "message-row bot";
    var avatar = document.createElement("div"); avatar.className = "avatar bot"; avatar.textContent = "P";
    var wrap   = document.createElement("div"); wrap.className   = "bubble-wrap";
    var bubble = document.createElement("div"); bubble.className = "bubble bot";
    wrap.appendChild(bubble); wrap.appendChild(makeCopyBtn(bubble));
    row.appendChild(avatar); row.appendChild(wrap);
    group.appendChild(row); appendTimestamp(group, false);
    messagesEl.appendChild(group); scrollToBottom();
    return bubble;
  }

  function appendBotBubble(text) {
    var group  = document.createElement("div"); group.className  = "msg-group";
    var row    = document.createElement("div"); row.className    = "message-row bot";
    var avatar = document.createElement("div"); avatar.className = "avatar bot"; avatar.textContent = "P";
    var wrap   = document.createElement("div"); wrap.className   = "bubble-wrap";
    var bubble = document.createElement("div"); bubble.className = "bubble bot";
    renderBotBubble(bubble, text);
    wrap.appendChild(bubble); wrap.appendChild(makeCopyBtn(bubble));
    row.appendChild(avatar); row.appendChild(wrap);
    group.appendChild(row); appendTimestamp(group, false);
    messagesEl.appendChild(group); scrollToBottom();
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function appendEligibilityVerdicts(payload) {
    var items = Array.isArray(payload.items) ? payload.items : [];
    if (!items.length) return;

    var group  = document.createElement("div"); group.className  = "msg-group";
    var row    = document.createElement("div"); row.className    = "message-row bot";
    var avatar = document.createElement("div"); avatar.className = "avatar bot"; avatar.textContent = "P";
    var wrap   = document.createElement("div"); wrap.className   = "bubble-wrap";
    var bubble = document.createElement("div"); bubble.className = "bubble bot elig-verdict-bubble";

    var cardsHtml = items.map(function(item) {
      var status = item.status || "general";
      var reasons = Array.isArray(item.reasons) ? item.reasons : [];
      var reasonsHtml = reasons.length
        ? '<ul class="elig-verdict-reasons">' + reasons.map(function(reason) {
            return '<li>' + escapeHtml(reason) + '</li>';
          }).join("") + '</ul>'
        : "";

      return '' +
        '<div class="elig-verdict-card is-' + status + '">' +
          '<div class="elig-verdict-top">' +
            '<div class="elig-verdict-card-name">' + escapeHtml(item.card_name || "Eligibility Check") + '</div>' +
            '<div class="elig-verdict-badge is-' + status + '">' + escapeHtml((item.badge || "") + " " + (item.label || "")) + '</div>' +
          '</div>' +
          reasonsHtml +
        '</div>';
    }).join("");

    bubble.innerHTML =
      '<div class="elig-verdict-header">' +
        '<div>' +
          '<div class="elig-verdict-title">Eligibility Assessment</div>' +
          '<div class="elig-verdict-summary">' + escapeHtml(payload.summary || "Here is a quick summary of the cards checked.") + '</div>' +
        '</div>' +
      '</div>' +
      '<div class="elig-verdict-list">' + cardsHtml + '</div>';

    wrap.appendChild(bubble); wrap.appendChild(makeCopyBtn(bubble));
    row.appendChild(avatar); row.appendChild(wrap);
    group.appendChild(row); appendTimestamp(group, false);
    messagesEl.appendChild(group); scrollToBottom();
  }

  function appendUserBubble(text) {
    var group  = document.createElement("div"); group.className  = "msg-group user";
    var row    = document.createElement("div"); row.className    = "message-row user";
    var avatar = document.createElement("div"); avatar.className = "avatar user"; avatar.textContent = "U";
    var wrap   = document.createElement("div"); wrap.className   = "bubble-wrap";
    var bubble = document.createElement("div"); bubble.className = "bubble user";
    bubble.textContent = text;
    wrap.appendChild(bubble); row.appendChild(avatar); row.appendChild(wrap);
    group.appendChild(row); appendTimestamp(group, true);
    messagesEl.appendChild(group); scrollToBottom();
  }

  /* ── Markdown rendering ── */
  function fixMarkdown(raw) {
    var t = (raw || "").replace(/\r\n/g, "\n");
    t = t
      .replace(/\|\s+(Would you like to check your eligibility[^|]*)$/i, "|\n\n$1")
      .replace(/([^\n])\s+(#{1,3}\s)/g, "$1\n\n$2")
      .replace(/([^\n])\s+(\d+\.\s+\*\*)/g, "$1\n\n$2")
      .replace(/\s+[–-]\s+(Network:|Tier:|Banking:)/g, "\n   - $1")
      .replace(/([^\n])\n(\d+\.\s+\*\*)/g, "$1\n\n$2")
      .replace(/(#{1,3}[^\n]*)\n(\d+\.\s+\*\*)/g, "$1\n\n$2");
    var lines = t.split("\n"), result = [], inTable = false, headerSepSeen = false;
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i], trimmed = line.trim();
      var isPipeLine = trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.length > 2;
      var isSepLine  = /^\|[\s\-:|]+\|$/.test(trimmed);
      if (isPipeLine || isSepLine) {
        if (!inTable) { if (result.length && result[result.length-1].trim()) result.push(""); inTable = true; headerSepSeen = false; }
        if (isSepLine) { if (!headerSepSeen) { headerSepSeen = true; result.push(trimmed); } }
        else {
          if (inTable && !headerSepSeen) {
            var nextLine = (i+1 < lines.length) ? lines[i+1].trim() : "";
            if (!/^\|[\s\-:|]+\|$/.test(nextLine)) {
              result.push(trimmed);
              var cols = Math.max(1, (trimmed.match(/\|/g)||[]).length - 1);
              result.push("|" + " --- |".repeat(cols)); headerSepSeen = true; continue;
            }
          }
          result.push(trimmed);
        }
      } else if (inTable && trimmed === "") {
        continue;
      } else {
        if (inTable) { result.push(""); inTable = false; headerSepSeen = false; }
        if (/^-{3,}$/.test(trimmed) || /^={3,}$/.test(trimmed)) continue;
        result.push(line);
      }
    }
    t = result.join("\n")
      .replace(/\n{3,}/g, "\n\n")
      .replace(/([^\n])\n(#{1,3}\s)/g, "$1\n\n$2")
      .replace(/([^\n])\n(\d+\.\s+\*\*)/g, "$1\n\n$2");
    return t.trim();
  }

  function renderStreamingBubble(bubble, rawText) {
    bubble.classList.remove("has-table");
    bubble.classList.add("streaming");
    bubble.textContent = rawText || "";
  }

  function isPipeTableLine(line) {
    var trimmed = (line || "").trim();
    return trimmed.indexOf("|") >= 0 && (trimmed.match(/\|/g) || []).length >= 2;
  }

  function isPipeSeparatorLine(line) {
    var trimmed = (line || "").trim();
    return /^\|?[\s:|-]+\|[\s:|-]*$/.test(trimmed) && trimmed.indexOf("-") >= 0;
  }

  function normalizePipeRow(line) {
    var row = (line || "").trim();
    if (!row.startsWith("|")) row = "| " + row;
    if (!row.endsWith("|")) row += " |";
    return row;
  }

  function pipeCells(line) {
    var row = normalizePipeRow(line);
    return row.slice(1, -1).split("|").map(function(cell) {
      return cell.trim();
    });
  }

  function buildFallbackTable(rawText) {
    var text = fixMarkdown(rawText);
    var lines = text.split("\n");
    var start = -1;
    for (var i = 0; i < lines.length; i++) {
      if (isPipeTableLine(lines[i]) && !isPipeSeparatorLine(lines[i])) {
        start = i;
        break;
      }
    }
    if (start < 0) return null;

    var header = pipeCells(lines[start]);
    if (header.length < 2) return null;

    var before = lines.slice(0, start).join("\n").trim();
    var afterStart = lines.length;
    var dataCells = [];
    for (var j = start + 1; j < lines.length; j++) {
      var line = lines[j].trim();
      if (!line) {
        afterStart = j + 1;
        break;
      }
      if (!isPipeTableLine(line)) {
        afterStart = j;
        break;
      }
      if (isPipeSeparatorLine(line)) continue;
      dataCells = dataCells.concat(pipeCells(line).filter(function(cell) { return cell !== ""; }));
    }

    var width = header.length;
    var rows = [];
    while (dataCells.length >= width) {
      rows.push(dataCells.slice(0, width));
      dataCells = dataCells.slice(width);
    }
    if (dataCells.length && rows.length) {
      rows[rows.length - 1][width - 1] = (rows[rows.length - 1][width - 1] + " " + dataCells.join(" ")).trim();
    }
    if (!rows.length) return null;

    return {
      before: before,
      after: lines.slice(afterStart).join("\n").trim(),
      header: header,
      rows: rows
    };
  }

  function fallbackTableToHtml(tableParts) {
    var head = "<thead><tr>" + tableParts.header.map(function(cell) {
      return "<th>" + escapeHtml(cell) + "</th>";
    }).join("") + "</tr></thead>";
    var body = "<tbody>" + tableParts.rows.map(function(row) {
      return "<tr>" + row.map(function(cell) {
        return "<td>" + escapeHtml(cell) + "</td>";
      }).join("") + "</tr>";
    }).join("") + "</tbody>";
    return "<table>" + head + body + "</table>";
  }

  function renderTableBubble(bubble, beforeHtml, tableHtml, afterHtml) {
    bubble.classList.remove("streaming");
    bubble.classList.add("has-table"); bubble.innerHTML = "";
    if (beforeHtml) { var d1 = document.createElement("div"); d1.className = "bubble-text"; d1.innerHTML = beforeHtml; bubble.appendChild(d1); }
    var tw = document.createElement("div"); tw.className = "table-wrapper"; tw.innerHTML = tableHtml; bubble.appendChild(tw);
    if (afterHtml) { var d2 = document.createElement("div"); d2.className = "bubble-footer"; d2.innerHTML = afterHtml; bubble.appendChild(d2); }
  }

  function buildStructuredResponseHtml(html) {
    var wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    var blocks = Array.prototype.slice.call(wrapper.children || []);
    var textLength = (wrapper.textContent || "").trim().length;
    if (blocks.length < 5 && textLength < 900) return html;

    var splitIndex = -1;
    var visibleBlocks = 0;
    for (var i = 0; i < blocks.length; i++) {
      var tag = (blocks[i].tagName || "").toLowerCase();
      if (tag === "h2" && visibleBlocks >= 2) {
        splitIndex = i;
        break;
      }
      visibleBlocks += 1;
      if (visibleBlocks >= 4 && splitIndex < 0) splitIndex = i + 1;
    }
    if (splitIndex <= 0 || splitIndex >= blocks.length) return html;

    var summaryHtml = blocks.slice(0, splitIndex).map(function(node) { return node.outerHTML; }).join("");
    var detailsHtml = blocks.slice(splitIndex).map(function(node) { return node.outerHTML; }).join("");
    return (
      '<div class="summary-block">' + summaryHtml + '</div>' +
      '<details class="details-toggle">' +
        '<summary>' + UI[lang].moreDetails + '</summary>' +
        '<div class="details-toggle-body">' + detailsHtml + '</div>' +
      '</details>'
    );
  }

  function addResponseChrome(bubble, meta) {
    if (!meta || !meta.intent) return;
    var metaWrap = document.createElement("div");
    metaWrap.className = "response-meta";
    metaWrap.innerHTML =
      '<span class="meta-pill intent">' + escapeHtml(intentLabel(meta.intent)) + '</span>' +
      '<span class="meta-pill confidence">' + escapeHtml(sourceConfidenceText(meta)) + '</span>';
    bubble.insertBefore(metaWrap, bubble.firstChild);

    var cards = Array.isArray(meta.cards) ? meta.cards.filter(Boolean) : [];
    if (cards.length) {
      var strip = document.createElement("div");
      strip.className = "card-pill-strip";
      cards.slice(0, 4).forEach(function(card) {
        var pill = document.createElement("span");
        pill.className = "card-pill";
        pill.textContent = card;
        strip.appendChild(pill);
      });
      bubble.insertBefore(strip, metaWrap.nextSibling);
    }
  }

  function renderBotBubble(bubble, rawText, meta) {
    var md = fixMarkdown(rawText), html = marked.parse(md);
    if (!/<table[\s>]/i.test(html)) {
      var fallbackTable = buildFallbackTable(rawText);
      if (fallbackTable) {
        renderTableBubble(
          bubble,
          fallbackTable.before ? marked.parse(fallbackTable.before) : "",
          fallbackTableToHtml(fallbackTable),
          fallbackTable.after ? marked.parse(fallbackTable.after) : ""
        );
        addResponseChrome(bubble, meta);
        return;
      }
      bubble.classList.remove("has-table");
      bubble.classList.remove("streaming");
      bubble.innerHTML = buildStructuredResponseHtml(html);
      addResponseChrome(bubble, meta);
      return;
    }
    var fallbackForWeakTable = buildFallbackTable(rawText);
    if (fallbackForWeakTable && !/<td[\s>]/i.test(html)) {
      renderTableBubble(
        bubble,
        fallbackForWeakTable.before ? marked.parse(fallbackForWeakTable.before) : "",
        fallbackTableToHtml(fallbackForWeakTable),
        fallbackForWeakTable.after ? marked.parse(fallbackForWeakTable.after) : ""
      );
      addResponseChrome(bubble, meta);
      return;
    }
    var tStart = html.search(/<table[\s>]/i);
    var tEndIdx = html.lastIndexOf("</table>");
    var tEnd = tEndIdx >= 0 ? tEndIdx + "</table>".length : html.length;
    var before = html.slice(0, tStart).trim(), table = html.slice(tStart, tEnd).trim(), after = html.slice(tEnd).trim();
    renderTableBubble(bubble, before, table, after);
    addResponseChrome(bubble, meta);
  }

  /* ── Thinking ── */
  function showThinking() {
    var id = "think_" + Date.now();
    var group = document.createElement("div"); group.id = id; group.className = "msg-group";
    var thinkingLabel = UI[lang].thinking;
    group.innerHTML =
      '<div class="message-row bot">' +
        '<div class="avatar bot">P</div>' +
        '<div class="bubble-wrap">' +
          '<div class="bubble bot" style="padding:0;">' +
            '<div class="thinking-indicator">' +
              '<div class="thinking-head">' +
                '<span class="thinking-text">' + thinkingLabel + '</span>' +
                '<div class="thinking-dots"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div>' +
                '<span class="thinking-elapsed" id="' + id + '_elapsed"></span>' +
              '</div>' +
              '<div class="thinking-current" id="' + id + '_current"></div>' +
              '<div class="thinking-progress-bar"><div class="thinking-progress-fill" id="' + id + '_bar"></div></div>' +
              '<div class="thinking-steps" id="' + id + '_steps"></div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>';
    messagesEl.appendChild(group);
    thinkStart = Date.now();
    thinkTimer = setInterval(function() {
      var el = document.getElementById(id + "_elapsed");
      if (el) el.textContent = Math.floor((Date.now() - thinkStart) / 1000) + "s";
    }, 1000);
    scrollToBottom();
    return id;
  }

  function updateThinkingProgress(id, message, stage) {
    var stepsEl = document.getElementById(id + "_steps");
    if (!stepsEl || !message) return;
    var currentEl = document.getElementById(id + "_current");
    var barEl = document.getElementById(id + "_bar");
    var stageOrder = ["classify", "search", "comparison", "product_details", "how_to_apply", "existing_cardholder", "catalog_query", "response"];
    var stageIndex = stageOrder.indexOf(stage || "");
    if (currentEl) currentEl.textContent = message;
    if (barEl) {
      var width = stageIndex >= 0 ? Math.max(20, ((stageIndex + 1) / stageOrder.length) * 100) : 42;
      barEl.style.width = width + "%";
    }
    var existing = Array.prototype.slice.call(stepsEl.querySelectorAll(".thinking-step"));
    var found = existing.find(function(el) { return el.textContent === message; });
    existing.forEach(function(el) {
      el.classList.remove("active");
      el.classList.add("done");
    });
    if (!found) {
      found = document.createElement("div");
      found.className = "thinking-step";
      found.textContent = message;
      stepsEl.appendChild(found);
    }
    found.classList.remove("done");
    found.classList.add("active");
  }

  function removeThinking(id) {
    var el = document.getElementById(id); if (el) el.remove();
    if (thinkTimer) { clearInterval(thinkTimer); thinkTimer = null; }
  }

  /* ── Follow-up chips ── */

  function appendFollowupChips(meta) {
    var chips = buildFollowupActions(meta);
    var container = document.createElement("div"); container.className = "follow-chips";
    chips.forEach(function(label) {
      var btn = document.createElement("button"); btn.className = "follow-chip"; btn.textContent = label;
      btn.onclick = function() { container.remove(); sendSuggestion(label); };
      container.appendChild(btn);
    });
    var groups = messagesEl.querySelectorAll(".msg-group");
    var lastGroup = groups[groups.length - 1];
    if (lastGroup) lastGroup.appendChild(container); else messagesEl.appendChild(container);
    scrollToBottom();
  }

  /* ── Calculators ── */

  function formatPercent(value) {
    var n = parseFloat(value);
    if (isNaN(n)) return "0";
    return Number.isInteger(n) ? String(n) : String(n);
  }

  function formatBDT(value) {
    if (value === null || value === undefined || value === "") return "";
    var n = parseInt(value, 10);
    if (isNaN(n)) return "";
    return "BDT " + n.toLocaleString();
  }

  function normalizeEMITerms(raw) {
    raw = raw || {};
    var tenures = Array.isArray(raw.tenures) ? raw.tenures : [12, 24, 36];
    tenures = tenures.map(function(value) { return parseInt(value, 10); })
      .filter(function(value, idx, arr) { return value > 0 && arr.indexOf(value) === idx; });
    if (!tenures.length) tenures = [12, 24, 36];

    var feePercent = parseFloat(raw.fee_percent);
    if (isNaN(feePercent)) feePercent = 1;

    var interestRate = parseFloat(raw.interest_rate_percent);
    if (isNaN(interestRate)) interestRate = 0;

    var minAmount = raw.min_amount === null || raw.min_amount === undefined || raw.min_amount === ""
      ? null
      : parseInt(raw.min_amount, 10);
    if (isNaN(minAmount)) minAmount = null;

    return {
      card_name: raw.card_name || "",
      tenures: tenures,
      fee_percent: feePercent,
      interest_rate_percent: interestRate,
      min_amount: minAmount,
      fee_label: raw.fee_label || "Conversion Fee",
      note: raw.note || "0% interest at partner stores; 1% one-time conversion fee applies."
    };
  }

  function normalizeEMIConfig(config) {
    var fallback = normalizeEMITerms((config || {}).default || {});
    var cards = Array.isArray((config || {}).cards) ? config.cards : [];
    cards = cards.map(normalizeEMITerms);
    if (!cards.length) cards = [fallback];

    var selected = 0;
    var selectedCard = (config || {}).selected_card || "";
    if (selectedCard) {
      cards.forEach(function(card, idx) {
        if (card.card_name === selectedCard) selected = idx;
      });
    }

    return { cards: cards, selectedIndex: selected };
  }

  function getActiveEMITerms() {
    if (!activeEMICalcConfig || !activeEMICalcConfig.cards.length) {
      return normalizeEMITerms({});
    }
    return activeEMICalcConfig.cards[activeEMICardIndex] || activeEMICalcConfig.cards[0];
  }

  function renderTenureButtonsHTML(terms) {
    return terms.tenures.map(function(months) {
      var active = months === emiTenure ? " active" : "";
      return '<button class="t-btn' + active + '" data-m="' + months + '" onclick="pickTenure(this)">' + months + ' mo</button>';
    }).join("");
  }

  function syncEMIDisplayTerms() {
    var terms = getActiveEMITerms();
    var feePct = formatPercent(terms.fee_percent);
    var feeLabel = document.getElementById("emi_fee_label");
    var note = document.getElementById("emi_note");
    var context = document.getElementById("emi_context");

    if (feeLabel) feeLabel.textContent = terms.fee_label + " (" + feePct + "%)";
    if (note) note.textContent = terms.note;
    if (context) {
      var label = terms.card_name ? terms.card_name : "General Prime Bank EMI terms";
      context.innerHTML = "Using <strong>" + escapeHtml(label) + "</strong>";
      if (terms.min_amount) {
        context.innerHTML += " - minimum purchase " + escapeHtml(formatBDT(terms.min_amount));
      }
    }
  }

  function createEMICalcBubble(config) {
    activeEMICalcConfig = normalizeEMIConfig(config);
    activeEMICardIndex = activeEMICalcConfig.selectedIndex;
    var terms = getActiveEMITerms();
    emiTenure = terms.tenures.indexOf(12) >= 0 ? 12 : terms.tenures[0];

    var cardPicker = "";
    if (activeEMICalcConfig.cards.length > 1) {
      var options = activeEMICalcConfig.cards.map(function(card, idx) {
        var selected = idx === activeEMICardIndex ? " selected" : "";
        return '<option value="' + idx + '"' + selected + '>' + escapeHtml(card.card_name || "General EMI") + '</option>';
      }).join("");
      cardPicker = '<div class="calc-field"><label>Card</label><select class="calc-select" id="emi_card" onchange="pickEMICard(this)">' + options + '</select></div>';
    }

    var group = document.createElement("div"); group.className = "msg-group";
    var row   = document.createElement("div"); row.className   = "message-row bot";
    var av    = document.createElement("div"); av.className    = "avatar bot"; av.textContent = "P";
    var wrap  = document.createElement("div"); wrap.className  = "bubble-wrap";
    var bub   = document.createElement("div"); bub.className   = "bubble bot calc-bubble";
    bub.innerHTML =
      '<div class="calc-hdr"><svg width="15" height="15" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/></svg>0% EMI Calculator</div>' +
      '<div class="calc-body">' +
        '<div class="calc-context" id="emi_context"></div>' +
        cardPicker +
        '<div class="calc-field"><label>Purchase Amount (BDT)</label><input type="number" class="calc-input" id="emi_amt" placeholder="e.g. 100,000" min="0" oninput="calcEMI()" /></div>' +
        '<div class="calc-warning" id="emi_warning"></div>' +
        '<div class="calc-field"><label>Tenure</label><div class="tenure-row" id="emi_tenures">' + renderTenureButtonsHTML(terms) + '</div></div>' +
        '<div class="calc-results"><div class="calc-row"><span class="calc-row-label">Monthly EMI</span><span class="calc-row-val" id="emi_monthly">BDT \u2014</span></div><div class="calc-row"><span class="calc-row-label">Total Payable</span><span class="calc-row-val" id="emi_total">\u2014</span></div><div class="calc-row"><span class="calc-row-label" id="emi_fee_label">Conversion Fee (1%)</span><span class="calc-row-val" id="emi_fee">\u2014</span></div></div>' +
        '<p class="calc-note" id="emi_note"></p>' +
      '</div>';
    wrap.appendChild(bub); row.appendChild(av); row.appendChild(wrap);
    group.appendChild(row); appendTimestamp(group, false);
    messagesEl.appendChild(group); scrollToBottom();
    syncEMIDisplayTerms();
  }

  function pickEMICard(select) {
    activeEMICardIndex = parseInt(select.value, 10) || 0;
    var terms = getActiveEMITerms();
    if (terms.tenures.indexOf(emiTenure) < 0) {
      emiTenure = terms.tenures.indexOf(12) >= 0 ? 12 : terms.tenures[0];
    }
    var tenureRow = document.getElementById("emi_tenures");
    if (tenureRow) tenureRow.innerHTML = renderTenureButtonsHTML(terms);
    syncEMIDisplayTerms();
    calcEMI();
  }

  function pickTenure(btn) {
    (btn.parentNode || document).querySelectorAll(".t-btn").forEach(function(b) { b.classList.remove("active"); });
    btn.classList.add("active"); emiTenure = parseInt(btn.dataset.m); calcEMI();
  }
  function calcEMI() {
    var terms = getActiveEMITerms();
    var amt = parseFloat((document.getElementById("emi_amt") || {}).value || 0);
    var warning = document.getElementById("emi_warning");
    if (warning) { warning.textContent = ""; warning.classList.remove("visible"); }
    if (!amt || amt <= 0) {
      document.getElementById("emi_monthly").textContent = "BDT \u2014";
      document.getElementById("emi_total").textContent   = "\u2014";
      document.getElementById("emi_fee").textContent     = "\u2014"; return;
    }
    if (warning && terms.min_amount && amt < terms.min_amount) {
      warning.textContent = "This card's EMI terms mention a minimum purchase of " + formatBDT(terms.min_amount) + ".";
      warning.classList.add("visible");
    }
    var fee = Math.ceil(amt * (terms.fee_percent || 0) / 100);
    document.getElementById("emi_monthly").textContent = "BDT " + Math.ceil(amt / emiTenure).toLocaleString();
    document.getElementById("emi_total").textContent   = "BDT " + Math.ceil(amt + fee).toLocaleString();
    document.getElementById("emi_fee").textContent     = "BDT " + fee.toLocaleString();
  }

  function createRewardsCalcBubble() {
    var group = document.createElement("div"); group.className = "msg-group";
    var row   = document.createElement("div"); row.className   = "message-row bot";
    var av    = document.createElement("div"); av.className    = "avatar bot"; av.textContent = "P";
    var wrap  = document.createElement("div"); wrap.className  = "bubble-wrap";
    var bub   = document.createElement("div"); bub.className   = "bubble bot calc-bubble";
    bub.innerHTML =
      '<div class="calc-hdr"><svg width="15" height="15" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>Rewards Calculator</div>' +
      '<div class="calc-body">' +
        '<div class="calc-field"><label>Monthly Spend (BDT)</label><input type="number" class="calc-input" id="rwd_spend" placeholder="e.g. 50,000" min="0" oninput="calcRewards()" /></div>' +
        '<div class="calc-results"><div class="calc-row"><span class="calc-row-label">Points / Month</span><span class="calc-row-val" id="rwd_month">\u2014</span></div><div class="calc-row"><span class="calc-row-label">Points / Year</span><span class="calc-row-val" id="rwd_year">\u2014</span></div><div class="calc-row"><span class="calc-row-label">Est. Redemption Value</span><span class="calc-row-val" id="rwd_value">\u2014</span></div></div>' +
        '<p class="calc-note">1 point per BDT 50 on POS & e-commerce \xB7 excludes cash advances & fees \xB7 500 pts \u2248 BDT 250</p>' +
      '</div>';
    wrap.appendChild(bub); row.appendChild(av); row.appendChild(wrap);
    group.appendChild(row); appendTimestamp(group, false);
    messagesEl.appendChild(group); scrollToBottom();
  }

  function calcRewards() {
    var spend = parseFloat((document.getElementById("rwd_spend") || {}).value || 0);
    if (!spend || spend <= 0) {
      document.getElementById("rwd_month").textContent = "\u2014";
      document.getElementById("rwd_year").textContent  = "\u2014";
      document.getElementById("rwd_value").textContent = "\u2014"; return;
    }
    var ptsMonth = Math.floor(spend / 50), ptsYear = ptsMonth * 12;
    document.getElementById("rwd_month").textContent = ptsMonth.toLocaleString();
    document.getElementById("rwd_year").textContent  = ptsYear.toLocaleString();
    document.getElementById("rwd_value").textContent = "BDT " + Math.floor(ptsYear * 0.5).toLocaleString();
  }

  /* ── Eligibility form ── */
  function renderEligibilityForm(schema) {
    var formId   = "elig_" + Date.now(); activeFormId = formId;
    var prefill  = schema.prefill || {}, hasPrefill = Object.keys(prefill).length > 0;
    var targetCard = schema.target_card || "", fields = schema.fields || {};
    var recommendedCards = schema.recommended_cards || [];
    var scopedCards = schema.scoped_cards || [];

    var group  = document.createElement("div"); group.className  = "msg-group"; group.id = formId + "_grp";
    var row    = document.createElement("div"); row.className    = "message-row bot"; row.id = formId + "_row";
    var avatar = document.createElement("div"); avatar.className = "avatar bot"; avatar.textContent = "P";
    var wrap   = document.createElement("div"); wrap.className   = "bubble-wrap";
    var bubble = document.createElement("div"); bubble.className = "bubble bot elig-bubble";

    var targetHtml   = targetCard ? '<div class="elig-form-target">Checking eligibility for: <strong>' + targetCard + '</strong></div>' : "";
    var recommendedHtml = (!targetCard && recommendedCards.length > 1)
      ? '<div class="elig-form-target">Checking eligibility for your recommended cards: <strong>' + recommendedCards.join(", ") + '</strong></div>'
      : "";
    var scopedHtml = (!targetCard && !recommendedHtml && scopedCards.length > 1)
      ? '<div class="elig-form-target">Checking eligibility for these cards: <strong>' + scopedCards.join(", ") + '</strong></div>'
      : "";
    var prefillBadge = hasPrefill ? '<span class="prefill-badge">Pre-filled from conversation</span>' : "";

    var fieldsHtml = "";
    Object.keys(fields).forEach(function(key) {
      var f = fields[key], req = f.required ? '<span class="req">*</span>' : "", pre = prefill[key];
      if (f.type === "number") {
        fieldsHtml += '<div class="elig-field"><label for="' + formId + '_' + key + '">' + f.label + ' ' + req + '</label>' +
          '<input type="number" id="' + formId + '_' + key + '" data-key="' + key + '"' +
          ' placeholder="' + (f.placeholder || "") + '"' +
          (f.min !== undefined ? ' min="' + f.min + '"' : "") +
          (f.max !== undefined ? ' max="' + f.max + '"' : "") +
          (pre !== undefined   ? ' value="' + pre + '"'  : "") + ' /></div>';
      } else if (f.type === "select") {
        var opts = '<option value="" disabled selected>Select...</option>';
        (f.options || []).forEach(function(o) {
          var sel = pre !== undefined && String(o.value) === String(pre) ? " selected" : "";
          opts += '<option value="' + o.value + '"' + sel + '>' + o.label + '</option>';
        });
        fieldsHtml += '<div class="elig-field"><label for="' + formId + '_' + key + '">' + f.label + ' ' + req + '</label>' +
          '<select id="' + formId + '_' + key + '" data-key="' + key + '">' + opts + '</select></div>';
      } else if (f.type === "checkbox") {
        var chkd = pre ? " checked" : "";
        fieldsHtml += '<div class="elig-checkbox-row"><input type="checkbox" id="' + formId + '_' + key + '" data-key="' + key + '"' + chkd + ' />' +
          '<label for="' + formId + '_' + key + '">' + f.label + '</label></div>';
      }
    });

    bubble.innerHTML =
      '<div class="elig-form" id="' + formId + '">' +
        '<div class="elig-form-header"><div class="elig-form-icon"><svg viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg></div>' +
          '<div><div class="elig-form-title">Eligibility Check ' + prefillBadge + '</div>' + targetHtml + recommendedHtml + scopedHtml + '</div></div>' +
        '<div class="elig-form-grid">' + fieldsHtml + '</div>' +
        '<div class="elig-form-errors" id="' + formId + '_errors"></div>' +
        '<div class="elig-form-actions">' +
          '<button class="elig-btn elig-btn-cancel" onclick="cancelEligForm(\'' + formId + '\')">Cancel</button>' +
          '<button class="elig-btn elig-btn-submit" id="' + formId + '_submit" onclick="submitEligForm(\'' + formId + '\', \'' + targetCard + '\', ' + JSON.stringify(scopedCards).replace(/"/g, '&quot;') + ')">Check Eligibility</button>' +
        '</div>' +
      '</div>';

    wrap.appendChild(bubble); row.appendChild(avatar); row.appendChild(wrap);
    group.appendChild(row); appendTimestamp(group, false);
    messagesEl.appendChild(group); scrollToBottom();
  }

  function submitEligForm(formId, targetCard, scopedCards) {
    var formEl = document.getElementById(formId); if (!formEl) return;
    var errorsEl = document.getElementById(formId + "_errors"); errorsEl.innerHTML = "";
    var formData = {}, errors = [];
    formEl.querySelectorAll("input[data-key], select[data-key]").forEach(function(el) {
      var key = el.dataset.key;
      if (el.type === "checkbox")    formData[key] = el.checked;
      else if (el.type === "number") formData[key] = el.value.trim() !== "" ? Number(el.value) : null;
      else                           formData[key] = el.value;
    });
    if (!formData.age || formData.age < 18 || formData.age > 70)            { errors.push("Age must be between 18 and 70.");          markFieldError(formId, "age"); }
    if (!formData.employment_type)                                            { errors.push("Please select an employment status.");      markFieldError(formId, "employment_type"); }
    if (!formData.monthly_income || formData.monthly_income <= 0)            { errors.push("Please enter a valid monthly income.");     markFieldError(formId, "monthly_income"); }
    if (formData.employment_duration_years === null || formData.employment_duration_years === undefined || formData.employment_duration_years === "") {
      errors.push("Please select employment duration (years)."); markFieldError(formId, "employment_duration_years");
    }
    if (errors.length > 0) { errorsEl.innerHTML = errors.map(function(e) { return "<p>" + e + "</p>"; }).join(""); scrollToBottom(); return; }
    if (targetCard) formData.target_card = targetCard;
    if (Array.isArray(scopedCards) && scopedCards.length > 0) formData.scoped_cards = scopedCards;
    formEl.classList.add("elig-form-submitted");
    var sb = document.getElementById(formId + "_submit"); if (sb) { sb.disabled = true; sb.textContent = "Checking..."; }
    activeThinkId = showThinking(); startLoading();
    ws.send(JSON.stringify({ type: "eligibility_form_submit", form_data: formData, session_id: sessionId }));
  }

  function cancelEligForm(formId) {
    var grp = document.getElementById(formId + "_grp"); if (grp) grp.remove(); activeFormId = null;
  }

  /* Preference form — content built from server-side PREFERENCE_FORM_SCHEMA constant, no user data */
  function renderPreferenceForm(schema) {
    var formId = "pref_" + Date.now(); activeFormId = formId;
    var fields = schema.fields || {};
    var prefill = schema.prefill || {};
    var hasPrefill = Object.keys(prefill).length > 0;

    var group  = document.createElement("div"); group.className = "msg-group"; group.id = formId + "_grp";
    var row    = document.createElement("div"); row.className = "message-row bot";
    var avatar = document.createElement("div"); avatar.className = "avatar bot"; avatar.textContent = "P";
    var wrap   = document.createElement("div"); wrap.className = "bubble-wrap";
    var bubble = document.createElement("div"); bubble.className = "bubble bot pref-bubble";

    var outer = document.createElement("div"); outer.id = formId;

    var hdr = document.createElement("div"); hdr.className = "pref-form-header";
    hdr.innerHTML = '<div class="pref-form-icon"><svg viewBox="0 0 24 24"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg></div>';
    var hdrText = document.createElement("div");
    var t1 = document.createElement("div"); t1.className = "pref-form-title"; t1.innerHTML = 'Find Your Perfect Card' + (hasPrefill ? ' <span class="prefill-badge">Pre-filled from conversation</span>' : '');
    var t2 = document.createElement("div"); t2.className = "pref-form-subtitle"; t2.textContent = "Answer a few quick questions for a more accurate recommendation";
    hdrText.appendChild(t1); hdrText.appendChild(t2); hdr.appendChild(hdrText);
    outer.appendChild(hdr);

    Object.keys(fields).forEach(function(key) {
      var f = fields[key];
      var section = document.createElement("div"); section.className = "pref-section";
      var lbl = document.createElement("div"); lbl.className = "pref-section-label";
      lbl.textContent = f.label;
      if (f.required) { var req = document.createElement("span"); req.style.color = "var(--error)"; req.textContent = " *"; lbl.appendChild(req); }
      section.appendChild(lbl);

      if (f.type === "button_group") {
        var grpEl = document.createElement("div"); grpEl.className = "pref-btn-group"; grpEl.id = formId + "_" + key;
        (f.options || []).forEach(function(o) {
          var btn = document.createElement("button"); btn.type = "button"; btn.className = "pref-pill";
          btn.setAttribute("data-group", key); btn.setAttribute("data-value", o.value);
          if (prefill[key] !== undefined && String(prefill[key]) === String(o.value)) btn.classList.add("selected");
          btn.textContent = o.label; btn.onclick = function() { selectPrefPill(btn); };
          grpEl.appendChild(btn);
        });
        section.appendChild(grpEl);
      } else if (f.type === "tile_grid") {
        var grid = document.createElement("div"); grid.className = "pref-tile-grid"; grid.id = formId + "_" + key;
        (f.options || []).forEach(function(o) {
          var tile = document.createElement("button"); tile.type = "button"; tile.className = "pref-tile";
          tile.setAttribute("data-group", key); tile.setAttribute("data-value", o.value);
          if (prefill[key] !== undefined && String(prefill[key]) === String(o.value)) tile.classList.add("selected");
          tile.textContent = o.label; tile.onclick = function() { selectPrefTile(tile); };
          grid.appendChild(tile);
        });
        section.appendChild(grid);
      }
      outer.appendChild(section);
    });

    var errDiv = document.createElement("div"); errDiv.id = formId + "_errors"; outer.appendChild(errDiv);

    var actions = document.createElement("div"); actions.className = "pref-form-actions";
    var cancelBtn = document.createElement("button"); cancelBtn.className = "pref-cancel-btn";
    cancelBtn.textContent = "Cancel"; cancelBtn.onclick = function() { cancelPrefForm(formId); };
    var submitBtn = document.createElement("button"); submitBtn.className = "pref-submit-btn"; submitBtn.id = formId + "_submit";
    submitBtn.textContent = "Get Recommendations"; submitBtn.onclick = function() { submitPrefForm(formId); };
    actions.appendChild(cancelBtn); actions.appendChild(submitBtn); outer.appendChild(actions);

    bubble.appendChild(outer); wrap.appendChild(bubble); row.appendChild(avatar); row.appendChild(wrap);
    group.appendChild(row); appendTimestamp(group, false);
    messagesEl.appendChild(group); scrollToBottom();
  }

  function selectPrefPill(btn) {
    var container = btn.closest(".pref-btn-group");
    if (container) container.querySelectorAll(".pref-pill").forEach(function(b) { b.classList.remove("selected"); });
    btn.classList.add("selected");
  }

  function selectPrefTile(tile) {
    var container = tile.closest(".pref-tile-grid");
    if (container) container.querySelectorAll(".pref-tile").forEach(function(t) { t.classList.remove("selected"); });
    tile.classList.add("selected");
  }

  function submitPrefForm(formId) {
    var formEl = document.getElementById(formId); if (!formEl) return;
    var errorsEl = document.getElementById(formId + "_errors"); errorsEl.textContent = "";
    var formData = {}, errors = [];
    formEl.querySelectorAll("[data-group].selected").forEach(function(el) {
      formData[el.getAttribute("data-group")] = el.getAttribute("data-value");
    });
    if (!formData.banking_type) errors.push("Please select a banking preference.");
    if (!formData.use_case)     errors.push("Please select a primary use case.");
    if (!formData.income_band) errors.push("Please select your monthly income band.");
    if (!formData.travel_frequency) errors.push("Please select your travel frequency.");
    if (!formData.tier_preference) errors.push("Please select a card tier preference.");
    if (errors.length > 0) {
      errors.forEach(function(e) {
        var p = document.createElement("p"); p.textContent = e;
        p.style.cssText = "font-size:12px;color:var(--error);margin:2px 0";
        errorsEl.appendChild(p);
      });
      scrollToBottom(); return;
    }
    formEl.classList.add("pref-form-submitted");
    var sb = document.getElementById(formId + "_submit"); if (sb) { sb.disabled = true; sb.textContent = "Finding cards..."; }
    activeThinkId = showThinking(); startLoading();
    ws.send(JSON.stringify({ type: "preference_form_submit", form_data: formData, session_id: sessionId }));
  }

  function cancelPrefForm(formId) {
    var grp = document.getElementById(formId + "_grp"); if (grp) grp.remove(); activeFormId = null;
  }

  function markFieldError(formId, key) {
    var el = document.getElementById(formId + "_" + key); if (!el) return;
    el.classList.add("field-error");
    el.addEventListener("input",  function() { el.classList.remove("field-error"); }, { once: true });
    el.addEventListener("change", function() { el.classList.remove("field-error"); }, { once: true });
  }

  /* ── Input & send ── */
  function sendMessage() {
    var text = inputEl.value.trim();
    if (!text || isLoading || !wsReady) return;
    if (welcomeEl) welcomeEl.style.display = "none";
    appendUserBubble(text);
    inputEl.value = ""; inputEl.style.height = "auto"; updateSendBtn();
    streamQueue = "";
    activeThinkId = showThinking(); startLoading();
    ws.send(JSON.stringify({ type: "message", message: text + getBengaliSuffix(), session_id: sessionId }));
  }

  function sendSuggestion(text) { inputEl.value = text; autoResize(inputEl); sendMessage(); }
  function autoResize(el) { el.style.height = "auto"; el.style.height = Math.min(el.scrollHeight, 140) + "px"; }
  function handleKey(e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }
  function updateSendBtn() { if (!isLoading && wsReady) sendBtnEl.disabled = !inputEl.value.trim(); }

  /* ── UI state ── */
  function startLoading()  { isLoading = true; sendBtnEl.disabled = true; inputEl.disabled = true; }
  function finishLoading() { isLoading = false; if (wsReady) { inputEl.disabled = false; sendBtnEl.disabled = !inputEl.value.trim(); inputEl.focus(); } }
  function setInputEnabled(enabled) { if (!isLoading) { inputEl.disabled = !enabled; sendBtnEl.disabled = !enabled || !inputEl.value.trim(); } }

  function setStatus(s) {
    var map = { online: { color: "#22c55e", anim: "pulse-dot 2s infinite", label: "Online" }, offline: { color: "#ef4444", anim: "none", label: "Reconnecting..." }, connecting: { color: "#f59e0b", anim: "pulse-dot 1s infinite", label: "Connecting..." } };
    var cfg = map[s] || map.offline;
    statusDot.style.background = cfg.color; statusDot.style.animation = cfg.anim; statusText.textContent = cfg.label;
  }

  function clearConversation() {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "clear", session_id: sessionId }));
    sessionId = null; activeBubble = null; fullText = ""; activeFormId = null; streamQueue = ""; lastDoneMeta = null;
    if (activeThinkId) { removeThinking(activeThinkId); activeThinkId = null; }
    messagesEl.querySelectorAll(".msg-group").forEach(function(el) { el.remove(); });
    if (welcomeEl) welcomeEl.style.display = "flex";
    inputEl.placeholder = UI[lang].placeholder;
    if (!isLoading) finishLoading();
  }

  /* ── Scroll FAB ── */
  function scrollToBottom() {
    var threshold = 200;
    var atBottom = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < threshold;
    if (atBottom) requestAnimationFrame(function() { messagesEl.scrollTop = messagesEl.scrollHeight; });
    updateScrollFab();
  }
  function updateScrollFab() {
    var atBottom = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 100;
    scrollFab.classList.toggle("visible", !atBottom && messagesEl.scrollHeight > messagesEl.clientHeight);
  }
  messagesEl.addEventListener("scroll", updateScrollFab);
  scrollFab.addEventListener("click", function() { messagesEl.scrollTop = messagesEl.scrollHeight; scrollFab.classList.remove("visible"); });

  /* ── Init ── */
  applyUI();
  connect();
