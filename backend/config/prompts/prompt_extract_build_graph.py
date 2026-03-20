"""
This module contains the prompt for extracting entities and relationships from legal text.
"""

# Định nghĩa các biến sẽ được truyền vào prompt
# Điều này giúp dễ dàng theo dõi và quản lý các tham số
# mà không cần phải tìm kiếm trong một chuỗi dài.
# Các biến này sẽ được format vào chuỗi prompt bên dưới.
# Ví dụ: PROMPT.format(ENTITY_TYPES=some_variable, doc_name=another_variable)

EXTRACT_PROMPT = """Bạn là chuyên gia phân tích dữ liệu pháp luật. Hãy trích xuất các thực thể và mối quan hệ từ văn bản luật được cung cấp để xây dựng một đồ thị tri thức (Knowledge Graph) chính xác và có tính liên kết cao.

## QUY TẮC TRÍCH XUẤT THỰC THỂ (ENTITIES)
    Trích xuất mọi thực thể quan trọng thuộc danh mục: [{ENTITY_TYPES}].
    Cho phần này hãy trả về:
        + Tên thực thể (entity_name): VIẾT HOA TOÀN BỘ.
        + Loại thực thể (entity_type): 1 trong những lọai sau:[{ENTITY_TYPES}]
        + Mô tả (entity_description): Mô tả chi tiết về chức năng, quyền hạn, nghĩa vụ hoặc nội dung quy định của thực thể đó trong ngữ cảnh văn bản. Tuyệt đối không sử dụng các đại từ chỉ định hoặc từ thay thế (như: đây, đó, này, họ, nó, quy định ấy...). Thay vào đó, phải lặp lại chính xác tên thực thể hoặc nội dung cụ thể để đảm bảo mỗi mô tả đều có ý nghĩa độc lập.

    Lưu ý rằng:
        + Cho tất cả thực thể: Phải kèm theo tên của văn bản pháp luật {doc_name}. Hơn nữa, hãy biến các tên của văn bản luật thành chữ có dấu như sau:      
            - "bo_luat_dan_su_2015"  thành "Bộ Luật Dân Sự 2015"
            - "bo_luat_hinh_su_2015" thành "Bộ Luật Hình Sự 2015" 
            - "bo_luat_lao_dong_2019" thành "Bộ Luật Lao Động 2019"
            - "bo_luat_to_tung_hinh_su_2015" thành "Bộ Luật Tố Tụng Hình Sự 2015" 
            - "nghi_quyet_04_2025_NQ_HDTP_2025" thành "Nghị Quyết 04/2025/NQ-HĐTP"
            - "nghi_dinh_144_2021_ND_CP_2021" thành "Nghị Định 144/2021/NĐ-CP"
            - "phap_lenh_phong_chong_mai_dam_2003" thành "Pháp Lệnh Phòng Chống Mại Dâm"
            - "thong_tu_64_2019_TT_BCA_2019" thành "Thông Tư 64/2019/TT-BCA"
        + Vậy nên, các thực thể nên có tên theo format như sau: "ĐIỀU 1 của Bộ Luật Hình Sự 2015", "Điều 82 của Bộ Luật Tố Tụng Hình Sự 2015"   
## QUY TẮC TRÍCH XUẤT QUAN HỆ (RELATIONSHIPS)
    Xác định các mối liên kết giữa các thực thể đã trích xuất. Cho phần này, hãy trả về:
        + source_entity: Tên thực thể nguồn (từ bước 1)
        + target_entity: Tên thực thể đích (từ bước 1)
        + relationship_description: Giải thích rõ lý do tại sao hai thực thể này có quan hệ (ví dụ: "Cơ quan A ban hành Quy định B", "Điều X quy định hình phạt cho Hành vi Y"). Tuyệt đối không sử dụng các đại từ chỉ định hoặc từ thay thế (như: đây, đó, này, họ, nó, quy định 	ấy...). Thay vào đó, phải lặp lại chính xác tên thực thể hoặc nội dung cụ thể để đảm bảo mỗi mô tả đều có ý nghĩa độc lập.
        + relationship_strength: Điểm số từ 1-10 thể hiện mức độ chặt chẽ của mối liên kết pháp lý.
    Đặc biệt: Cho mọi trường hợp văn bản nhắc đến một Điều, Khoản hoặc Văn bản luật khác (kể cả dẫn chiếu nội bộ), bắt buộc tạo quan hệ "dẫn chiếu tới"

## QUY TẮC TRÍCH XUẤT QUY ĐỊNH (CLAIMS)
    Trích xuất nội dung quy định: Với mỗi thực thể đã trích xuất, trích xuất các quy định liên quan mà thực thể đó là "Chủ thể thực hiện".
    Với mỗi quy định, trích xuất:
        + Chủ thể (Subject): Tên đối tượng/nhóm đối tượng phải thực thi quy định (VIẾT HOA).
        + Đối tượng liên quan (Object): Cơ quan quản lý, hoặc bên chịu tác động của quy định này. Nếu không có, dùng **NONE**.
        + Loại quy định (Claim Type): Phân loại (ví dụ: NGHĨA VỤ, QUYỀN HẠN, ĐIỀU KIỆN, HÀNH VI CẤM).
        + Trạng thái (Claim Status): **TRUE** (Đang có hiệu lực), **SUSPECTED** (Cần kiểm tra văn bản).
        - Mô tả chi tiết (Claim Description): Nội dung cụ thể của quy định, các điều kiện kèm theo và hệ quả pháp lý.
        - Thời điểm (Claim Date): Khoảng thời gian (Ngày bắt đầu, Ngày kết thúc) theo định dạng ISO-8601. Nếu chỉ có một mốc thời gian, dùng mốc đó cho cả hai. Nếu không rõ, dùng **NONE**.
        - Trích dẫn (Claim Source Text): Danh sách **tất cả** các câu trích nguyên văn từ văn bản gốc có liên quan đến quy định này. Gộp các câu trích dẫn thành 1 chuỗi ký tự.

## ĐỊNH DẠNG ĐẦU RA (BẮT BUỘC)
    Trả về danh sách các phần tử cách nhau bởi dấu ##. Mỗi phần tử tuân thủ cấu trúc sau:
        + Thực thể: ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>) {record_delimiter}
        + Quan hệ: ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>) {record_delimiter}
        + Quy định: ("claim"{tuple_delimiter}<subject_entity>{tuple_delimiter}<object_entity>{tuple_delimiter}<claim_type>{tuple_delimiter}<claim_status>{tuple_delimiter}<claim_start_date>{tuple_delimiter}<claim_end_date>{tuple_delimiter}<claim_description>{tuple_delimiter}<claim_source>) {record_delimiter}
        + Kết thúc bằng: {completion_delimiter}
    NGÔN NGỮ: Chỉ sử dụng Tiếng Việt hoàn chỉnh. Tuyệt đối không sử dụng tiếng Trung, tiếng Anh hay bất kỳ ngôn ngữ nào khác.
    ĐỊNH DẠNG: Chỉ trả về dữ liệu trích xuất, không giải thích thêm bằng tiếng Trung.

## VÍ DỤ MẪU ĐỂ BẠN LÀM THEO:
Text: Chính phủ ban hành Nghị định 123/2024/NĐ-CP. Theo đó, người điều khiển xe máy điện không đội mũ bảo hiểm sẽ bị phạt tiền từ 400.000 đến 600.000 đồng. 
Output: 
("entity"{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}VĂN_BẢN_PHÁP_LUẬT{tuple_delimiter}Nghị định 123/2024/NĐ-CP quy định về xử phạt vi phạm hành chính trong lĩnh vực giao thông đường bộ) {record_delimiter} 
(“entity"{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}HÀNH_VI_VI_PHẠM{tuple_delimiter}Hành vi người điều khiển xe máy điện không đội mũ bảo hiểm cho người đi mô tô, xe máy) {record_delimiter}
("entity"{tuple_delimiter}PHẠT TIỀN TỪ 400.000 ĐẾN 600.000 ĐỒNG{tuple_delimiter}CHẾ_TÀI_PHÁP_LÝ{tuple_delimiter}Mức phạt tiền từ 400.000 đồng đến 600.000 đồng áp dụng cho hành vi vi phạm giao thông cụ thể) {record_delimiter} 
("relationship"{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}Nghị định 123/2024/NĐ-CP xác định hành vi không đội mũ bảo hiểm là hành vi vi phạm pháp luật{tuple_delimiter}9) {record_delimiter} 
("relationship"{tuple_delimiter}KHÔNG ĐỘI MŨ BẢO HIỂM{tuple_delimiter}PHẠT TIỀN TỪ 400.000 ĐẾN 600.000 ĐỒNG{tuple_delimiter}Hành vi không đội mũ bảo hiểm dẫn đến hình thức xử phạt tiền từ 400.000 đến 600.000 đồng{tuple_delimiter}10) {completion_delimiter}
("claim"{tuple_delimiter}NGƯỜI ĐIỀU KHIỂN XE MÁY ĐIỆN{tuple_delimiter}NGHỊ ĐỊNH 123/2024/NĐ-CP{tuple_delimiter}HÀNH VI BỊ NGHIÊM CẤM{tuple_delimiter}TRUE{tuple_delimiter}2024-01-01{tuple_delimiter}NONE{tuple_delimiter}Không đội mũ bảo hiểm bị xử phạt hành chính mức 400.000 - 600.000 VNĐ.{tuple_delimiter}"người điều khiển xe máy điện không đội mũ bảo hiểm sẽ bị phạt tiền từ 400.000 đến 600.000 đồng")                        
"""
