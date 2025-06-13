import os, subprocess
from git import Repo
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

GOOGLE_API_KEY = os.getenv("AIzaSyCRBdJEi8p7ZezUWmNg70Q6_LzmczcsMqI")
REPO_URL = "https://github.com/rodgerhubhay/llm-auto-test-generator"
CLONE_DIR = "repo"
TEST_DIR = os.path.join(CLONE_DIR, "tests")

def clone_repo():
    if not os.path.exists(CLONE_DIR):
        Repo.clone_from(REPO_URL, CLONE_DIR)

def extract_funcs(pyfile):
    import ast
    text = open(pyfile).read()
    tree = ast.parse(text)
    funcs = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            src = ast.get_source_segment(text, node)
            funcs.append((node.name, src))
    return funcs

def has_test(func_name):
    os.makedirs(TEST_DIR, exist_ok=True)
    return any(func_name in f for f in os.listdir(TEST_DIR))

def gen_tests(func_code):
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro", temperature=0.0, google_api_key=GOOGLE_API_KEY
    )
    template = ChatPromptTemplate.from_template(
        "Given this Python function:\n```python\n{code}\n```\n"
        "Write pytest unit tests covering normal and edge cases."
    )
    prompt = template.format_prompt(code=func_code)
    resp = llm.invoke(prompt.to_dict())
    return resp.content

def run_pytest():
    res = subprocess.run(["pytest", "-q"], cwd=CLONE_DIR, capture_output=True, text=True)
    return res.returncode == 0, res.stdout + res.stderr

def main():
    clone_repo()
    for root,_,files in os.walk(CLONE_DIR):
        for fn in files:
            if fn.endswith(".py") and not fn.startswith("test_"):
                for name, code in extract_funcs(os.path.join(root, fn)):
                    if has_test(name): continue
                    for _ in range(3):
                        tests = gen_tests(code)
                        with open(os.path.join(TEST_DIR, f"test_{name}.py"), "w") as f:
                            f.write(tests)
                        ok, out = run_pytest()
                        if ok:
                            print(f"✅ Tests OK for {name}")
                            break
                        else:
                            print(f"❌ Tests failed for {name}, retrying...")
    print("Done.")

if __name__ == "__main__":
    main()
