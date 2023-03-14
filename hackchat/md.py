def create_table(rows: list[str], items: list[tuple]) -> str:
    header = '|'.join(rows) + '|\n' + '|'.join(['---' for i in range(len(rows))])
    data = '\n'.join('|'.join(item) for item in items)
    return header + '\n' + data