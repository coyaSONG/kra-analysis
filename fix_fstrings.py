#!/usr/bin/env python3
"""
f-string quote nesting 문제를 일괄 수정하는 스크립트
Python 3.11에서는 f-string 내부에 외부와 같은 따옴표를 사용할 수 없음
"""

import os
import re

def fix_fstring_quotes(content):
    """
    f-string 내부의 double quote를 single quote로 변경
    """
    # f"...{dict["key"]}..." 패턴을 찾아서 f"...{dict['key']}..."로 변경
    def replace_inner_quotes(match):
        fstring = match.group(0)
        # f-string 내부의 {} 블록들을 찾아서 처리
        def fix_brace_content(brace_match):
            content = brace_match.group(1)
            # 내부의 double quotes를 single quotes로 변경
            fixed_content = content.replace('"', "'")
            return '{' + fixed_content + '}'

        # f"..." 내부의 {...} 블록들 처리
        fixed_fstring = re.sub(r'\{([^}]+)\}', fix_brace_content, fstring)
        return fixed_fstring

    # f"..." 패턴 찾기 (중첩된 따옴표 포함)
    pattern = r'f"[^"]*(?:\{[^}]*"[^}]*\}[^"]*)*"'
    content = re.sub(pattern, replace_inner_quotes, content)

    return content

def process_file(filepath):
    """파일 처리"""
    try:
        with open(filepath, encoding='utf-8') as f:
            original_content = f.read()

        fixed_content = fix_fstring_quotes(original_content)

        if fixed_content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            print(f"✅ Fixed: {filepath}")
            return True
        else:
            print(f"⚪ No changes: {filepath}")
            return False
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        return False

def main():
    """메인 함수"""
    print("🔧 f-string quote nesting 문제 일괄 수정 시작...")

    # Python 파일들 찾기 - 전체 프로젝트 대상
    python_files = []
    search_dirs = ['packages/scripts', 'apps/api', 'apps/collector/src']

    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(os.path.join(root, file))

    print(f"📁 총 {len(python_files)}개 Python 파일 발견")

    fixed_count = 0
    for filepath in python_files:
        if process_file(filepath):
            fixed_count += 1

    print(f"\n✨ 완료! {fixed_count}개 파일 수정됨")

if __name__ == '__main__':
    main()
