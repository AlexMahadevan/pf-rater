"""
Custom CSS styling for PolitiFact Jurisprudence Assistant.
Distinctive design that avoids generic "AI slop" aesthetics.
"""

def get_custom_css():
    """Return custom CSS with distinctive design elements."""
    return """
    <style>
    /* Import distinctive fonts - Crimson Pro for headers, Source Serif for body */
    @import url('https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap');
    
    /* CSS Variables for Design System */
    :root {
        --primary-red: #E63946;
        --primary-red-dim: rgba(230, 57, 70, 0.15);
        --primary-red-glow: rgba(230, 57, 70, 0.4);
        
        --true-green: #06D6A0;
        --true-green-dim: rgba(6, 214, 160, 0.15);
        
        --false-amber: #FFB627;
        --false-amber-dim: rgba(255, 182, 39, 0.15);
        
        --bg-dark: #0D1117;
        --bg-panel: #161B22;
        --bg-panel-hover: #1C2128;
        --bg-input: #010409;
        
        --text-primary: #E6EDF3;
        --text-secondary: #7D8590;
        --text-muted: #484F58;
        
        --border-subtle: #30363D;
        --border-emphasis: #6E7681;
        
        /* Animated gradient background */
        --gradient-1: #0D1117;
        --gradient-2: #1a1625;
        --gradient-3: #1e1b2e;
    }
    
    /* Main app background with layered animated gradient */
    .stApp {
        background: linear-gradient(125deg, var(--gradient-1) 0%, var(--gradient-2) 50%, var(--gradient-3) 100%);
        background-size: 200% 200%;
        animation: gradientShift 15s ease infinite;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Crimson Pro', serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: var(--text-primary) !important;
    }
    
    p, li, div:not([class*="st-"]), span:not([class*="st-"]), label {
        font-family: 'Source Serif 4', serif !important;
        color: var(--text-primary) !important;
    }
    
    /* Ensure Streamlit icons and specific Material symbols keep their intended font */
    .st-emotion-cache-1vt4y6f, .material-icons, [class^="st-"] svg {
        font-family: 'Material Icons' !important;
    }
    
    /* Main title styling with glow effect */
    h1 {
        font-size: 3.5rem !important;
        background: linear-gradient(135deg, var(--text-primary) 0%, var(--primary-red) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem !important;
        text-shadow: 0 0 40px var(--primary-red-glow);
        animation: titlePulse 3s ease-in-out infinite;
    }
    
    @keyframes titlePulse {
        0%, 100% { opacity: 0.95; }
        50% { opacity: 1; }
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.5rem;
        background-color: transparent;
        border-bottom: 2px solid var(--border-subtle);
    }
    
    .stTabs [data-baseweb="tab"] {
        font-family: 'Crimson Pro', serif !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        color: var(--text-secondary) !important;
        padding: 0.75rem 1.5rem !important;
        background-color: transparent !important;
        border: none !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--primary-red) !important;
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        color: var(--primary-red) !important;
        border-bottom: 3px solid var(--primary-red) !important;
    }
    
    /* Input fields with depth */
    textarea, input {
        font-family: 'Source Serif 4', serif !important;
        background-color: var(--bg-input) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        transition: all 0.3s ease;
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.4);
    }
    
    textarea:focus, input:focus {
        border-color: var(--primary-red) !important;
        box-shadow: 0 0 0 3px var(--primary-red-dim), inset 0 2px 8px rgba(0,0,0,0.4) !important;
        outline: none !important;
    }
    
    /* Buttons with premium feel */
    .stButton > button {
        font-family: 'Crimson Pro', serif !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        background: linear-gradient(135deg, var(--primary-red) 0%, #c41e3a 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 2rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px var(--primary-red-dim);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button:before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    
    .stButton > button:hover:before {
        left: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px var(--primary-red-glow);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Info/Success/Warning/Error boxes with custom glass morphism */
    .stAlert {
        border-radius: 16px !important;
        border: 1px solid var(--border-subtle) !important;
        backdrop-filter: blur(12px);
        padding: 1.5rem !important;
        animation: slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .stSuccess {
        background: linear-gradient(135deg, var(--true-green-dim) 0%, rgba(6, 214, 160, 0.05) 100%) !important;
        border-left: 4px solid var(--true-green) !important;
    }
    
    .stInfo {
        background: linear-gradient(135deg, var(--primary-red-dim) 0%, rgba(230, 57, 70, 0.05) 100%) !important;
        border-left: 4px solid var(--primary-red) !important;
    }
    
    .stWarning {
        background: linear-gradient(135deg, var(--false-amber-dim) 0%, rgba(255, 182, 39, 0.05) 100%) !important;
        border-left: 4px solid var(--false-amber) !important;
    }
    
    .stError {
        background: linear-gradient(135deg, rgba(230, 57, 70, 0.2) 0%, rgba(230, 57, 70, 0.05) 100%) !important;
        border-left: 4px solid var(--primary-red) !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-family: 'Crimson Pro', serif !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        background-color: var(--bg-panel) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        background-color: var(--bg-panel-hover) !important;
        border-color: var(--border-emphasis) !important;
        transform: translateX(4px);
    }
    
    .streamlit-expanderContent {
        background-color: var(--bg-panel) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 0 0 12px 12px !important;
        padding: 1.5rem !important;
    }
    
    /* Checkbox styling */
    .stCheckbox {
        color: var(--text-primary) !important;
    }
    
    .stCheckbox > label {
        font-family: 'Source Serif 4', serif !important;
        font-size: 1rem !important;
    }
    
    /* Progress bars */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--primary-red) 0%, var(--false-amber) 100%) !important;
        border-radius: 8px !important;
        height: 12px !important;
    }
    
    /* Code blocks if any */
    code {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: var(--bg-input) !important;
        color: var(--true-green) !important;
        padding: 0.2rem 0.5rem !important;
        border-radius: 6px !important;
    }
    
    /* Links */
    a {
        color: var(--primary-red) !important;
        text-decoration: none !important;
        border-bottom: 1px solid transparent;
        transition: all 0.3s ease;
    }
    
    a:hover {
        border-bottom-color: var(--primary-red);
        filter: brightness(1.2);
    }
    
    /* Sidebar if used */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-panel) 0%, var(--bg-dark) 100%) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    
    /* Spinner customization */
    .stSpinner > div {
        border-top-color: var(--primary-red) !important;
        border-right-color: var(--primary-red) !important;
    }
    
    /* Caption text */
    .stCaptionContainer, .caption {
        font-family: 'Source Serif 4', serif !important;
        color: var(--text-secondary) !important;
        font-style: italic !important;
    }
    
    /* Custom badge animations */
    @keyframes badgePulse {
        0%, 100% {
            box-shadow: 0 0 0 0 var(--primary-red-glow);
        }
        50% {
            box-shadow: 0 0 0 8px transparent;
        }
    }
    
    .consensus-badge {
        animation: badgePulse 2s infinite;
    }
    
    /* Dividers */
    hr {
        border: none !important;
        border-top: 1px solid var(--border-subtle) !important;
        margin: 2rem 0 !important;
        opacity: 0.5;
    }
    
    /* File uploader */
    [data-testid="stFileUploadDropzone"] {
        background-color: var(--bg-panel) !important;
        border: 2px dashed var(--border-subtle) !important;
        border-radius: 16px !important;
        transition: all 0.3s ease;
    }
    
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: var(--primary-red) !important;
        background-color: var(--bg-panel-hover) !important;
    }
    
    /* Columns */
    [data-testid="column"] {
        gap: 1rem;
    }
    
    /* Smooth fade-in for all content */
    .element-container {
        animation: fadeIn 0.5s ease-in;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    /* Hide the clickable anchor links next to headers */
    .stMarkdown h1 a, .stMarkdown h2 a, .stMarkdown h3 a, .stMarkdown h4 a, .stMarkdown h5 a, .stMarkdown h6 a {
        display: none !important;
    }
    
    /* Result card styling */
    .result-card {
        background: rgba(22, 27, 34, 0.6);
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        backdrop-filter: blur(8px);
    }
    
    .result-card:hover {
        border-color: #E63946;
        transform: translateX(4px);
    }
    
    /* Source context card styling */
    .source-context-card {
        background: linear-gradient(135deg, rgba(230, 57, 70, 0.1) 0%, rgba(230, 57, 70, 0.05) 100%);
        border: 1px solid #30363D;
        border-left: 4px solid #E63946;
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        backdrop-filter: blur(12px);
        animation: slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stats-box {
        background: rgba(13, 17, 23, 0.4);
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    </style>
    """
