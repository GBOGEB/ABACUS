def check_brackets(expression):
    """
    Function to check if all brackets in the given expression are balanced.
    Supports (), {}, and [].
    """
    stack = []
    bracket_map = {')': '(', '}': '{', ']': '['}

    for char in expression:
        if char in bracket_map.values():
            stack.append(char)
        elif char in bracket_map.keys():
            if stack and stack[-1] == bracket_map[char]:
                stack.pop()
            else:
                return False

    return len(stack) == 0


if __name__ == "__main__":
    # Example usage
    test_expression = input("Enter an expression to check for balanced brackets: ")
    if check_brackets(test_expression):
        print("The brackets are balanced.")
    else:
        print("The brackets are not balanced.")