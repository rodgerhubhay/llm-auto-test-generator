import os, subprocess, ast
from git import Repo
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

REPO_URL = os.getenv("REPO_URL", "<YOUR_TARGET_REPO>")
CLONE_DIR = "repo"
TEST_DIR = os.path.join(CLONE_DIR, "tests")
os.makedirs(TEST_DIR, exist_ok=True)

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0,
                             google_api_key=os.getenv("GOOGLE_API_KEY"))

def clone_repo():
    if not os.path.exists(CLONE_DIR):
        Repo.clone_from(REPO_URL, CLONE_DIR)

def extract_functions(pyfile):
    with open(pyfile) as f: tree = ast.parse(f.read())
    funcs = [(node.name, ast.get_source_segment(open(pyfile).read(), node))
             for node in tree.body if isinstance(node, ast.FunctionDef)]
    return funcs

def has_test(func_name):
    # Fixed: Check for exact test file existence
    test_file = os.path.join(TEST_DIR, f"test_{func_name}.py")
    return os.path.exists(test_file)

def gen_tests(func_code):
    prompt = ChatPromptTemplate.from_template(
        "You are a Python test generator. Given this function:\n```python\n{code}\n```"
        "Write pytest tests that cover normal, edge, and invalid inputs."
    )
    # FIX: Removed .to_dict() since it's not needed
    return llm.invoke(prompt.format_prompt(code=func_code)).content

def run_pytest():
    proc = subprocess.run(["pytest", "-q"], cwd=CLONE_DIR, capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout + proc.stderr

def main():
    clone_repo()
    for root, _, files in os.walk(CLONE_DIR):
        for fn in files:
            if fn.endswith(".py") and not fn.startswith("test_"):
                pyfile = os.path.join(root, fn)
                for name, code in extract_functions(pyfile):
                    if has_test(name): 
                        continue
                    for attempt in range(3):
                        tests = gen_tests(code)
                        with open(os.path.join(TEST_DIR, f"test_{name}.py"), "w") as f:
                            f.write(tests)
                        ok, logs = run_pytest()
                        print(f"{'✅' if ok else '❌'} {name} (attempt {attempt+1})")
                        if ok: 
                            break

if __name__ == "__main__":
    main()
