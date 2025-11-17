import os

def generate_markdown_index(directory):
    """
    Generate a markdown index file for all markdown files in the given directory.

    Args:
        directory (str): The directory to scan for markdown files.

    Returns:
        str: The generated markdown index content.
    """
    markdown_files = [f for f in os.listdir(directory) if f.endswith('.md')]
    markdown_files.sort()

    index_content = "# Markdown Index\n\n"
    for file in markdown_files:
        file_path = os.path.join(directory, file)
        index_content += f"- [{file}]({file_path})\n"

    return index_content

def save_index_file(directory, content):
    """
    Save the generated markdown index content to a file.

    Args:
        directory (str): The directory to save the index file.
        content (str): The markdown index content.
    """
    index_file_path = os.path.join(directory, "INDEX.md")
    with open(index_file_path, "w") as index_file:
        index_file.write(content)

if __name__ == "__main__":
    target_directory = os.path.dirname(os.path.abspath(__file__))
    index_content = generate_markdown_index(target_directory)
    save_index_file(target_directory, index_content)
    print("INDEX.md has been generated.")