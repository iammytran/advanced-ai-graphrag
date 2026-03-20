"""
Evaluation script for RAG Chatbot using LangSmith.
Code adapted from LangChain LangSmith tutorials.
"""

import json
import os
import sys
from typing import TypedDict
import ast

from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline

# Import LLMs
from langchain_openai import ChatOpenAI
from langsmith import Client, traceable
from typing_extensions import Annotated

# Ensure we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mute warnings
import warnings

from backend.config.config import (
    HUGGINGFACE_MODEL,
    LANGSMITH_API_KEY,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
from backend.src.chatbot import Chatbot

warnings.filterwarnings("ignore")

# Initialize Chatbot
chatbot = Chatbot(model_option=2, retrieval_mode="graphrag_only")


def get_judge_llm():
    """Get the LLM to use for evaluation (Judge)"""
    # llm = HuggingFacePipeline.from_model_id(
    #     model_id=HUGGINGFACE_MODEL,
    #     task="text-generation",
    #     pipeline_kwargs={
    #         "max_new_tokens": 800,
    #         "temperature": 0.0,
    #         "do_sample": False,
    #     },
    # )
    # return ChatHuggingFace(llm=llm)
    llm = ChatOpenAI(
        # base_url="https://openrouter.ai/api/v1",
        model=OPENAI_MODEL,
        max_completion_tokens=800,
        temperature=0,
    )
    return llm


# --- Evaluator Definitions ---


# 1. Correctness Evaluator
class CorrectnessGrade(TypedDict):
    explanation: Annotated[str, ..., "Giải thích lý do cho điểm số"]
    correct: Annotated[bool, ..., "True nếu câu trả lời đúng, False nếu sai."]


correctness_instructions = """Bạn là một giáo viên đang chấm một bài kiểm tra. Bạn sẽ nhận được một CÂU HỎI, ĐÁP ÁN CHUẨN (đáp án đúng) và CÂU TRẢ LỜI CỦA HỌC SINH. Dưới đây là các tiêu chí chấm điểm cần tuân thủ:
(1) Chấm điểm câu trả lời của học sinh CHỈ dựa trên độ chính xác về mặt thông tin thực tế so với đáp án chuẩn.
(2) Đảm bảo rằng câu trả lời của học sinh không chứa bất kỳ phát biểu nào mâu thuẫn với nhau.
(3) Việc câu trả lời của học sinh chứa nhiều thông tin hơn đáp án chuẩn là hoàn toàn hợp lệ, miễn là các thông tin bổ sung đó vẫn chính xác về mặt thực tế so với đáp án chuẩn.

Đánh giá độ chính xác:
Giá trị True nghĩa là câu trả lời của học sinh đáp ứng được tất cả các tiêu chí trên.
Giá trị False nghĩa là câu trả lời của học sinh không đáp ứng được tất cả các tiêu chí trên.

Hãy giải thích lập luận của bạn theo từng bước để đảm bảo cả quá trình suy luận và kết luận của bạn đều chính xác. Tránh việc chỉ đưa ra kết luận (Đúng/Sai) ngay từ đầu câu trả lời."""


def correctness(inputs: dict, outputs: dict, reference_outputs: dict) -> bool:
    """An evaluator for RAG answer accuracy"""
    llm = get_judge_llm().with_structured_output(
        CorrectnessGrade, method="json_schema", strict=False
    )  # strict=False for broader compatibility

    answers = f"""\
CÂU HỎI: {inputs['question']}
ĐÁP ÁN CHUẨN: {reference_outputs['answer']}
CÂU TRẢ LỜI CỦA HỌC SINH: {outputs['answer']}"""

    grade = llm.invoke(
        [
            {"role": "system", "content": correctness_instructions},
            {"role": "user", "content": answers},
        ]
    )
    return grade["correct"]


# 2. Relevance Evaluator
class RelevanceGrade(TypedDict):
    explanation: Annotated[str, ..., "Giải thích chi tiết lý do cho điểm số"]
    relevant: Annotated[
        bool,
        ...,
        "Cung cấp điểm số (True/False) về việc câu trả lời có giải quyết được câu hỏi hay không",
    ]


relevance_instructions = """Bạn là một giáo viên đang chấm một bài kiểm tra. Bạn sẽ được cung cấp một CÂU HỎI và một CÂU TRẢ LỜI CỦA HỌC SINH. Dưới đây là các tiêu chí chấm điểm cần tuân thủ:

(1) Đảm bảo CÂU TRẢ LỜI CỦA HỌC SINH ngắn gọn và có liên quan đến CÂU HỎI.
(2) Đảm bảo CÂU TRẢ LỜI CỦA HỌC SINH giúp giải đáp CÂU HỎI.

Mức độ liên quan:
Giá trị mức độ liên quan là True có nghĩa là câu trả lời của học sinh đáp ứng tất cả các tiêu chí.
Giá trị mức độ liên quan là False có nghĩa là câu trả lời của học sinh không đáp ứng tất cả các tiêu chí.

Hãy giải thích lập luận của bạn theo từng bước để đảm bảo lập luận và kết luận của bạn là chính xác. Tránh việc chỉ đưa ra kết luận đúng ngay từ đầu."""


def relevance(inputs: dict, outputs: dict) -> bool:
    """A simple evaluator for RAG answer helpfulness."""
    llm = get_judge_llm().with_structured_output(
        RelevanceGrade, method="json_schema", strict=False
    )

    answer = (
        f"CÂU HỎI: {inputs['question']}\nCÂU TRẢ LỜI CỦA HỌC SINH: {outputs['answer']}"
    )
    grade = llm.invoke(
        [
            {"role": "system", "content": relevance_instructions},
            {"role": "user", "content": answer},
        ]
    )
    return grade["relevant"]


# 3. Groundedness Evaluator
class GroundedGrade(TypedDict):
    explanation: Annotated[str, ..., "Giải thích chi tiết lý do cho điểm số"]
    grounded: Annotated[
        bool,
        ...,
        "Cung cấp điểm số (True/False) về việc câu trả lời có chứa thông tin bịa đặt ngoài tài liệu hay không",
    ]


grounded_instructions = """Bạn là một giáo viên đang chấm một bài kiểm tra. Bạn sẽ được cung cấp các DỮ KIỆN và một CÂU TRẢ LỜI CỦA HỌC SINH. Dưới đây là các tiêu chí chấm điểm cần tuân thủ:
(1) Đảm bảo CÂU TRẢ LỜI CỦA HỌC SINH bám sát vào các DỮ KIỆN. 
(2) Đảm bảo CÂU TRẢ LỜI CỦA HỌC SINH không chứa thông tin "bịa đặt" (hallucinated) nằm ngoài phạm vi của các DỮ KIỆN.

Mức độ bám sát dữ kiện (Grounded):
Giá trị bám sát là True có nghĩa là câu trả lời của học sinh đáp ứng tất cả các tiêu chí.
Giá trị bám sát là False có nghĩa là câu trả lời của học sinh không đáp ứng tất cả các tiêu chí.

Hãy giải thích lập luận của bạn theo từng bước để đảm bảo lập luận và kết luận của bạn là chính xác. Tránh việc chỉ đưa ra kết luận đúng ngay từ đầu."""


def groundedness(inputs: dict, outputs: dict) -> bool:
    """A simple evaluator for RAG answer groundedness."""
    llm = get_judge_llm().with_structured_output(
        GroundedGrade, method="json_schema", strict=False
    )

    # Ensure documents are available and valid
    docs = outputs.get("documents", [])
    if not docs:
        return False  # No documents -> Not grounded (or trivial)

    doc_string = "\n\n".join(docs)  # Directly join strings
    answer = f"DỮ KIỆN: {doc_string}\nCÂU TRẢ LỜI CỦA HỌC SINH: {outputs['answer']}"

    grade = llm.invoke(
        [
            {"role": "system", "content": grounded_instructions},
            {"role": "user", "content": answer},
        ]
    )
    return grade["grounded"]


# 4. Retrieval Relevance Evaluator
class RetrievalRelevanceGrade(TypedDict):
    explanation: Annotated[str, ..., "Giải thích chi tiết lý do cho điểm số"]
    relevant: Annotated[
        bool,
        ...,
        "True nếu các tài liệu truy xuất được có liên quan đến câu hỏi, ngược lại là False",
    ]


retrieval_relevance_instructions = """Bạn là một giáo viên đang chấm một bài kiểm tra. Bạn sẽ được cung cấp một CÂU HỎI và một tập hợp các DỮ KIỆN do học sinh cung cấp. Dưới đây là các tiêu chí chấm điểm cần tuân thủ:

(1) Mục tiêu của bạn là xác định các DỮ KIỆN hoàn toàn KHÔNG liên quan đến CÂU HỎI.
(2) Nếu các dữ kiện chứa BẤT KỲ từ khóa hoặc ý nghĩa ngữ nghĩa nào liên quan đến câu hỏi, hãy coi chúng là có liên quan.
(3) Các dữ kiện có chứa MỘT SỐ thông tin không liên quan đến câu hỏi cũng KHÔNG SAO, miễn là tiêu chí (2) được đáp ứng.

Mức độ liên quan:
Giá trị mức độ liên quan là True có nghĩa là các DỮ KIỆN chứa BẤT KỲ từ khóa hoặc ý nghĩa ngữ nghĩa nào liên quan đến CÂU HỎI và do đó được coi là có liên quan.
Giá trị mức độ liên quan là False có nghĩa là các DỮ KIỆN hoàn toàn không liên quan đến CÂU HỎI.

Hãy giải thích lập luận của bạn theo từng bước để đảm bảo lập luận và kết luận của bạn là chính xác. Tránh việc chỉ đưa ra kết luận đúng ngay từ đầu."""


def retrieval_relevance(inputs: dict, outputs: dict) -> bool:
    """An evaluator for document relevance"""
    llm = get_judge_llm().with_structured_output(
        RetrievalRelevanceGrade, method="json_schema", strict=False
    )

    docs = outputs.get("documents", [])
    if not docs:
        return False

    doc_string = "\n\n".join(docs)  # Directly join strings
    answer = f"DỮ KIỆN: {doc_string}\nCÂU HỎI: {inputs['question']}"

    grade = llm.invoke(
        [
            {"role": "system", "content": retrieval_relevance_instructions},
            {"role": "user", "content": answer},
        ]
    )
    return grade["relevant"]


# 5. Chunk Recall Evaluator
def retrieval_recall(outputs: dict, reference_outputs: dict) -> dict:
    """
    Calculates the recall of retrieved chunks against the ground truth chunks.
    """
    # Lấy danh sách chunk IDs tham chiếu từ dataset
    # Đảm bảo nó luôn là một list
    referenced_chunks = reference_outputs.get("referenced_chunk_ids", [])
    if not isinstance(referenced_chunks, list):
        referenced_chunks = []

    # Lấy danh sách chunk IDs mà RAG đã truy xuất
    retrieved_chunks_raw = outputs.get("source_chunk_ids", [])
    retrieved_chunks = []
    if isinstance(retrieved_chunks_raw, str) and retrieved_chunks_raw.startswith("[") and retrieved_chunks_raw.endswith("]"):
        try:
            retrieved_chunks = ast.literal_eval(retrieved_chunks_raw)
        except (ValueError, SyntaxError):
            retrieved_chunks = [] # Giữ là list rỗng nếu parse lỗi
    elif isinstance(retrieved_chunks_raw, list):
        retrieved_chunks = retrieved_chunks_raw

    print(f"retrieved_chunks: {retrieved_chunks}")

    # Nếu không có chunk tham chiếu, không thể tính recall, trả về 0
    if not referenced_chunks:
        return {"score": 0}

    # Chuyển sang dạng set để xử lý tập hợp hiệu quả
    set_referenced = set(referenced_chunks)
    set_retrieved = set(retrieved_chunks)

    # Tìm các chunk ID có trong cả hai tập hợp
    intersecting_chunks = set_referenced.intersection(set_retrieved)

    # Tính recall
    recall_score = len(intersecting_chunks) / len(set_referenced)

    # LangSmith yêu cầu trả về một dict có key là 'score'
    return {"score": recall_score}


# --- Target Function and Main Execution ---


@traceable()
def target(inputs: dict) -> dict:
    """Run the RAG Chatbot"""
    # The chatbot.run() method returns the final state dict
    result = chatbot.chat(inputs["question"])
    return {
        "answer": result["answer"],
        # Ensure we pass the list of Document objects
        "documents": result["retrieved_documents"],
        "source_chunk_ids": result.get("source_chunk_ids", []),
    }


def main():
    # Helper to load data
    dataset_path = os.path.join("dataset", "qa.json")
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    # Initialize Client
    client = Client(api_key=LANGSMITH_API_KEY)

    # Dataset 1: Original Question
    dataset_name_original = "RAG_Eval_Dataset_Original"
    if not client.has_dataset(dataset_name=dataset_name_original):
        print(f"Creating dataset '{dataset_name_original}'...")
        dataset_original = client.create_dataset(dataset_name=dataset_name_original)

        for item in raw_data:
            client.create_example(
                inputs={"question": item["original_question"]},
                outputs={
                    "answer": item["answer"],
                    "referenced_chunk_ids": item.get("referenced_chunk_ids", []),
                },
                dataset_id=dataset_original.id,
            )
    else:
        print(f"Using existing dataset '{dataset_name_original}'")

    # # Dataset 2: Reframed Question
    # dataset_name_reframed = "RAG_Eval_Dataset_Reframed"
    # if not client.has_dataset(dataset_name=dataset_name_reframed):
    #     print(f"Creating dataset '{dataset_name_reframed}'...")
    #     dataset_reframed = client.create_dataset(dataset_name=dataset_name_reframed)

    #     for item in raw_data:
    #         client.create_example(
    #             inputs={"question": item["reframed_question"]},
    #             outputs={"answer": item["answer"]},
    #             dataset_id=dataset_reframed.id,
    #         )
    # else:
    #     print(f"Using existing dataset '{dataset_name_reframed}'")

    # Run Evaluation
    print(
        f"Starting evaluation with judges using {get_judge_llm().model_name if getattr(get_judge_llm(), 'model_name', None) else get_judge_llm().model_id}..."
    )

    print("\n--- Evaluating Original Questions Dataset ---")
    experiment_results_original = client.evaluate(
        target,
        data=dataset_name_original,
        evaluators=[correctness, groundedness, relevance, retrieval_recall],
        experiment_prefix="rag-chatbot-original",
        metadata={
            "description": "RAG Chatbot Evaluation - Original Questions",
            "llm_model": OPENAI_MODEL,
        },
    )

    # print("\n--- Evaluating Reframed Questions Dataset ---")
    # experiment_results_reframed = client.evaluate(
    #     target,
    #     data=dataset_name_reframed,
    #     evaluators=[correctness, groundedness, relevance, retrieval_relevance],
    #     experiment_prefix="rag-chatbot-reframed",
    #     metadata={
    #         "description": "RAG Chatbot Evaluation - Reframed Questions",
    #         "llm_model": OPENAI_MODEL,
    #     },
    # )
    df_results_original = experiment_results_original.to_pandas()
    # Force casting problematic ID columns to string
    print("Forcing ID columns to string type...")
    if 'example_id' in df_results_original.columns:
        df_results_original['example_id'] = df_results_original['example_id'].astype(str)
    if 'id' in df_results_original.columns:
        df_results_original['id'] = df_results_original['id'].astype(str)
        
    print("\nEvaluations Complete!")
    print(f"Original Question Results: {df_results_original}")

    # Lưu kết quả ra file JSON
    results_path = "evaluation_results.json"
    print(f"\n✅ Đang lưu kết quả đánh giá vào file: {results_path}")
    with open(results_path, 'w', encoding='utf-8') as f:
        df_results_original.to_json(f, orient="records", force_ascii=False, indent=4)
    print(f"✅ Đã lưu kết quả đánh giá vào file: {results_path}")
    # print(f"Reframed Question Results: {experiment_results_reframed.url}")


if __name__ == "__main__":
    main()