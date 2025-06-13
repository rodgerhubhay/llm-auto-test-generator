import os, subprocess, ast
from git import Repo
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# ====== CONFIG ======
REPO_URL = os.getenv("REPO_URL", "<YOUR_TARGET_REPO>")
CLONE_DIR = "repo"
TEST_DIR = os.path.join(CLONE_DIR, "tests")
os.makedirs(TEST_DIR, exist_ok=True)

# Create __init__.py so pytest detects the folder
with open(os.path.join(TEST_DIR, "__init__.py"), "w") as f:
    f.write("")

# ====== LLM SETUP ======
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# ====== CLONE REPO ======
def clone_repo():
    if not os.path.exists(CLONE_DIR):
        print(f"Cloning {REPO_URL}...")
        Repo.clone_from(REPO_URL, CLONE_DIR)
    else:
        print("Repo already cloned.")

# ====== EXTRACT PYTHON FUNCTIONS ======
def extract_functions(pyfile):
    with open(pyfile) as f:
        source = f.read()
        tree = ast.parse(source)
    funcs = [
        (node.name, ast.get_source_segment(source, node))
        for node in tree.body if isinstance(node, ast.FunctionDef)
    ]
    return funcs

# ====== CHECK IF TEST EXISTS ======
def has_test(func_name):
    return os.path.exists(os.path.join(TEST_DIR, f"test_{func_name}.py"))

# ====== GENERATE TEST CASES ======
def gen_tests(func_code):
    prompt = ChatPromptTemplate.from_template(
        "You are a Python test generator. Given this function:\n```python\n{code}\n```"
        "Write pytest tests that cover normal, edge, and invalid inputs."
    )
    return llm.invoke(prompt.format_prompt(code=func_code)).content

# ====== RUN PYTEST ======
def run_pytest():
    proc = subprocess.run(
        ["pytest", "tests", "-q"],
        cwd=CLONE_DIR, capture_output=True, text=True
    )
    return proc.returncode == 0, proc.stdout + proc.stderr

# ====== MAIN LOOP ======
def main():
    clone_repo()

    for root, _, files in os.walk(CLONE_DIR):
        for fn in files:
            if fn.endswith(".py") and not fn.startswith("test_"):
                pyfile = os.path.join(root, fn)
                for name, code in extract_functions(pyfile):
                    if has_test(name):
                        print(f"✔️ Skipping test for existing function: {name}")
                        continue
                    for attempt in range(3):
                        print(f"🔍 Generating test for {name} (attempt {attempt+1})")
                        tests = gen_tests(code)
                        test_file = os.path.join(TEST_DIR, f"test_{name}.py")
                        with open(test_file, "w") as f:
                            f.write(tests)
                        ok, logs = run_pytest()
                        print(logs)
                        if ok:
                            print(f"✅ Tests for {name} passed")
                            break
                        else:
                            print(f"❌ Tests for {name} failed")
    print("✅ Done generating and testing.")

if __name__ == "__main__":
    main()
