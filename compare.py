import sys
import os
import time
import importlib.util
from datetime import datetime

ROOT = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(ROOT, "shared"))

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from config import QUESTION

SEPARATOR = "=" * 70
DIVIDER = "-" * 70
MODELS = ["gpt-4o", "gpt-4o-mini"]


class Tee:
    """Tulis ke terminal dan file secara bersamaan."""

    def __init__(self, filepath: str):
        self.terminal = sys.stdout
        self.file = open(filepath, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.file.write(message)

    def flush(self):
        self.terminal.flush()
        self.file.flush()

    def close(self):
        self.file.close()


def load_module(folder: str):
    """Load modul assistant.py dari folder langgraph/ atau langchain/."""
    sys.path.insert(0, os.path.join(ROOT, folder))
    spec = importlib.util.spec_from_file_location(
        f"{folder}_assistant", os.path.join(ROOT, folder, "assistant.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def count_tool_calls(messages: list) -> tuple[int, list[str], int]:
    tool_names = []
    steps = 0
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            steps += 1
            for tc in msg.tool_calls:
                tool_names.append(tc["name"])
    return len(tool_names), tool_names, steps


def print_structured_steps(messages: list):
    """Cetak setiap langkah agent secara terstruktur dan mudah dibaca."""
    step = 0
    i = 0
    while i < len(messages):
        msg = messages[i]

        if isinstance(msg, AIMessage) and msg.tool_calls:
            step += 1
            print(f"\n  [Step {step}] Tool Calls")
            for tc in msg.tool_calls:
                args_str = ", ".join(f"{k}={v}" for k, v in tc["args"].items())
                print(f"    → {tc['name']:<25} {args_str}")

        elif isinstance(msg, ToolMessage):
            tool_results = []
            while i < len(messages) and isinstance(messages[i], ToolMessage):
                tool_results.append(messages[i])
                i += 1

            print(f"\n  [Step {step}] Tool Results")
            for tr in tool_results:
                content = tr.content.replace("\n", " ")
                print(f"    ✓ {tr.name:<25} {content}")
            continue

        elif isinstance(msg, AIMessage) and not msg.tool_calls:
            print(f"\n  [Final Answer]")
            text = msg.content if isinstance(msg.content, str) else msg.text
            for line in text.strip().split("\n"):
                print(f"    {line}")

        i += 1


def run_experiment(label: str, folder: str, model: str, question: str) -> dict:
    """Jalankan satu kombinasi framework + model dan catat metrik."""
    module = load_module(folder)
    assistant = module.build_assistant(model)

    print(f"\n{SEPARATOR}")
    print(f"  {label}  |  Model: {model}")
    print(SEPARATOR)

    all_messages = []
    start = time.time()
    for chunk in assistant.stream({"messages": [HumanMessage(question)]}):
        for _, values in chunk.items():
            for message in values.get("messages", []):
                all_messages.append(message)
    elapsed = time.time() - start

    print_structured_steps(all_messages)

    total_tools, tool_names, reasoning_steps = count_tool_calls(all_messages)

    print(f"\n  Selesai dalam {elapsed:.2f}s | {total_tools} tool calls | {reasoning_steps} step | {len(all_messages)} pesan")

    return {
        "label": label,
        "model": model,
        "elapsed": elapsed,
        "total_tools": total_tools,
        "tool_names": tool_names,
        "reasoning_steps": reasoning_steps,
        "messages": all_messages,
        "steps": len(all_messages),
    }


def print_summary(results: list[dict]):
    """Cetak tabel perbandingan semua kombinasi."""
    print(f"\n{SEPARATOR}")
    print("  RINGKASAN PERBANDINGAN")
    print(SEPARATOR)

    col = 16
    print(f"  {'Metrik':<22}" + "".join(
        f"  {r['label']+'/'+r['model']:>{col}}" for r in results
    ))
    print(f"  {DIVIDER}")
    print(f"  {'Waktu eksekusi':<22}" + "".join(
        f"  {r['elapsed']:>{col-1}.2f}s" for r in results
    ))
    print(f"  {'Tool calls':<22}" + "".join(
        f"  {r['total_tools']:>{col}}" for r in results
    ))
    print(f"  {'Jumlah step':<22}" + "".join(
        f"  {r['reasoning_steps']:>{col}}" for r in results
    ))
    print(f"  {'Jumlah pesan':<22}" + "".join(
        f"  {r['steps']:>{col}}" for r in results
    ))

    print(f"\n  Detail tools per kombinasi:")
    for r in results:
        print(f"  {DIVIDER}")
        print(f"  {r['label']} / {r['model']}: {' → '.join(r['tool_names'])}")

    print(SEPARATOR)


def write_markdown(results: list[dict], question: str, filepath: str):
    """Tulis hasil eksperimen ke file markdown yang rapi."""
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# Hasil Perbandingan: LangGraph vs LangChain\n\n")
        f.write(f"**Tanggal run:** {run_time}\n\n")
        f.write(f"**Pertanyaan:**\n> {question}\n\n")
        f.write(f"---\n\n")

        # Ringkasan tabel
        f.write(f"## Ringkasan\n\n")
        f.write(f"| Metrik | " + " | ".join(f"{r['label']} / {r['model']}" for r in results) + " |\n")
        f.write(f"|---|" + "---|" * len(results) + "\n")
        f.write(f"| Waktu eksekusi | " + " | ".join(f"{r['elapsed']:.2f}s" for r in results) + " |\n")
        f.write(f"| Tool calls | " + " | ".join(str(r['total_tools']) for r in results) + " |\n")
        f.write(f"| Jumlah step | " + " | ".join(str(r['reasoning_steps']) for r in results) + " |\n")
        f.write(f"| Jumlah pesan | " + " | ".join(str(r['steps']) for r in results) + " |\n")
        f.write(f"\n")

        # Urutan tools
        f.write(f"### Urutan Tools Dipanggil\n\n")
        for r in results:
            f.write(f"- **{r['label']} / {r['model']}:** {' → '.join(r['tool_names'])}\n")
        f.write(f"\n---\n\n")

        # Detail setiap eksperimen
        for r in results:
            f.write(f"## {r['label']} | Model: {r['model']}\n\n")

            step = 0
            i = 0
            messages = r["messages"]
            while i < len(messages):
                msg = messages[i]

                if isinstance(msg, AIMessage) and msg.tool_calls:
                    step += 1
                    f.write(f"### Step {step}\n\n")

                    # Tool Calls
                    f.write(f"**Tool Calls**\n\n")
                    for tc in msg.tool_calls:
                        args_str = ", ".join(f"`{k}={v}`" for k, v in tc["args"].items())
                        f.write(f"- `{tc['name']}` → {args_str}\n")
                    f.write(f"\n")

                    # Tool Results (langsung setelah tool calls)
                    i += 1
                    tool_results = []
                    while i < len(messages) and isinstance(messages[i], ToolMessage):
                        tool_results.append(messages[i])
                        i += 1

                    if tool_results:
                        f.write(f"**Tool Results**\n\n")
                        for tr in tool_results:
                            f.write(f"- `{tr.name}`\n```\n{tr.content}\n```\n\n")

                    f.write(f"---\n\n")
                    continue

                elif isinstance(msg, AIMessage) and not msg.tool_calls:
                    f.write(f"### Final Answer\n\n")
                    text = msg.content if isinstance(msg.content, str) else msg.text
                    f.write(f"{text.strip()}\n\n")

                i += 1

            f.write(f"**Selesai dalam {r['elapsed']:.2f}s | {r['total_tools']} tool calls | {r['steps']} pesan**\n\n")
            f.write(f"---\n\n")


if __name__ == "__main__":
    output_dir = os.path.join(ROOT, "results")
    os.makedirs(output_dir, exist_ok=True)

    txt_path = os.path.join(output_dir, "compare.txt")
    md_path = os.path.join(output_dir, "compare.md")

    tee = Tee(txt_path)
    sys.stdout = tee

    print(f"\n{SEPARATOR}")
    print(f"  PERTANYAAN")
    print(SEPARATOR)
    print(f"  {QUESTION}")

    experiments = [
        ("LangGraph", "langgraph"),
        ("LangChain", "langchain"),
    ]

    results = []
    for model in MODELS:
        for label, folder in experiments:
            results.append(run_experiment(label, folder, model, QUESTION))

    print_summary(results)

    # Kembalikan stdout ke terminal sebelum tutup file
    sys.stdout = tee.terminal
    tee.close()

    # Tulis file markdown terpisah yang lebih rapi
    write_markdown(results, QUESTION, md_path)

    print(f"\nHasil disimpan di:")
    print(f"  Plain text : results/compare.txt")
    print(f"  Markdown   : results/compare.md")
