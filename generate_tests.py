import os, subprocess, ast
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# ====== PATH SETUP ======
MODULE_FILE = "math_utils.py"
TEST_DIR = "tests"
os.makedirs(TEST_DIR, exist_ok=True)

# Create __init__.py so pytest detects test package
with open(os.path.join(TEST_DIR, "__init__.py"), "w") as f:
    f.write("")
with open("__init__.py", "w") as f:
    f.write("")

# ====== LLM SETUP ======
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# ====== EXTRACT PYTHON FUNCTIONS ======
def extract_functions(pyfile):
    with open(pyfile) as f:
        source = f.read()
        tree = ast.parse(source)
    return [
        (node.name, ast.get_source_segment(source, node))
        for node in tree.body if isinstance(node, ast.FunctionDef)
    ]

# ====== CHECK IF TEST EXISTS ======
def has_test(func_name):
    return os.path.exists(os.path.join(TEST_DIR, f"test_{func_name}.py"))

# ====== GENERATE TESTS WITH IMPORT ======
def gen_tests(func_code, func_name):
    prompt = ChatPromptTemplate.from_template(
        "You are a Python test generator. Given the following function from the file `math_utils.py`:\n"
        "```python\n{code}\n```\n"
        "Write a complete `pytest` test file that imports `{func}` from `math_utils`. "
        "Cover normal, edge, and invalid inputs with assertions."
    )
    result = llm.invoke(prompt.format_prompt(code=func_code, func=func_name)).content

    # Strip ```python ... ``` if present
    if result.strip().startswith("```"):
        result = result.strip().removeprefix("```python").removesuffix("```").strip()

    return result


# ====== RUN PYTEST ======
def run_pytest():
    proc = subprocess.run(
        ["pytest", TEST_DIR, "-q"],
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True, text=True
    )
    return proc.returncode == 0, proc.stdout + proc.stderr

# ====== MAIN SCRIPT ======
def main():
    print(f"🔍 Looking for functions in {MODULE_FILE}...")
    for func_name, func_code in extract_functions(MODULE_FILE):
        if has_test(func_name):
            print(f"✔️ Skipping existing test: {func_name}")
            continue

        for attempt in range(3):
            print(f"\n🧪 Generating test for `{func_name}` (attempt {attempt+1})")
            test_code = gen_tests(func_code, func_name)
            test_path = os.path.join(TEST_DIR, f"test_{func_name}.py")
            with open(test_path, "w") as f:
                f.write(test_code)

            ok, logs = run_pytest()
            print(logs)

            if ok:
                print(f"✅ Tests for `{func_name}` passed")
                break
            else:
                print(f"❌ Tests for `{func_name}` failed — retrying...")

    print("\n🎯 Test generation complete.")

if __name__ == "__main__":
    main()
