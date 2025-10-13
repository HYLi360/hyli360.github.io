import re

def get_yaml_attr(post_html_path: str) -> list:
    # 从 `_layouts/post.html` 中搜索 YAML Front Matter 可使用的属性。
    with open(post_html_path, "r", encoding="utf-8") as f:
        post_html = f.read()
    attr_list = re.findall(r"page\.([a-zA-Z0-9_\.]+)", post_html)
    return sorted(set(attr_list)) 

print(get_yaml_attr("/home/hyli360/文档/TechLib/post.html"))