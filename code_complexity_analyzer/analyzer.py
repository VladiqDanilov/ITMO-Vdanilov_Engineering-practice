import subprocess
import json
import re
import os
import sys

class CodeAnalyzer:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def run_pylint(self):
        result = subprocess.run(
            ["pylint", "--output-format=json", self.file_path],
            capture_output=True,
            text=True
        )
        return json.loads(result.stdout) if result.stdout else []

    def run_mypy(self):
        result = subprocess.run(
            ["mypy", "--json-report", "mypy_report", self.file_path],
            capture_output=True,
            text=True
        )
        return result.stdout

    def run_shellcheck(self):
        result = subprocess.run(
            ["shellcheck", self.file_path],
            capture_output=True,
            text=True
        )
        return result.stdout.splitlines()

    def analyze_fixtures(self):
        recommendations = []
        with open(self.file_path, "r", encoding="utf-8") as file:
            content = file.read()

            fixture_pattern = r"@pytest\.fixture\(.*?\)\s+def\s+(\w+)\(.*?\):"
            fixtures = re.findall(fixture_pattern, content, re.DOTALL)

            for fixture in fixtures:
                if "get_token_user_with_role" in content:
                    recommendations.append(
                        f"Фикстура '{fixture}': Использование функции 'get_token_user_with_role' напрямую. "
                        "Рекомендуется сделать фикстуру более универсальной, передавая параметры явно."
                    )
                if "scope=\"class\"" in content:
                    recommendations.append(
                        f"Фикстура '{fixture}': Использование 'scope=\"class\"'. "
                        "Убедитесь, что фикстура действительно нужна на уровне класса, чтобы избежать избыточного использования."
                    )
        return recommendations

    def analyze(self):
        file_extension = os.path.splitext(self.file_path)[1]

        if file_extension == ".py":
            pylint_results = self.run_pylint()
            mypy_results = self.run_mypy()
            fixture_recommendations = self.analyze_fixtures()

            return {
                "pylint": pylint_results,
                "mypy": mypy_results,
                "fixtures": fixture_recommendations
            }

        elif file_extension == ".sh":
            shellcheck_results = self.run_shellcheck()
            return {
                "shellcheck": shellcheck_results
            }

        return {}

    def generate_recommendations(self, results):
        recommendations = []

        for issue in results.get("pylint", []):
            recommendations.append(f"Pylint: {issue.get('message')} (Line {issue.get('line')})")

        if "error" in results.get("mypy", ""):
            recommendations.append("Mypy: Обнаружены ошибки статической типизации.")

        for fixture_recommendation in results.get("fixtures", []):
            recommendations.append(f"Fixture: {fixture_recommendation}")

        for shellcheck_issue in results.get("shellcheck", []):
            recommendations.append(f"ShellCheck: {shellcheck_issue}")

        return recommendations

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Укажите путь к файлу для анализа.")
        sys.exit(1)

    file_to_analyze = sys.argv[1]
    analyzer = CodeAnalyzer(file_to_analyze)
    analysis_results = analyzer.analyze()
    recommendations = analyzer.generate_recommendations(analysis_results)

    print("\nРекомендации по улучшению кода:")
    for rec in recommendations:
        print(f"- {rec}")
