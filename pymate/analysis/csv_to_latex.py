import csv


def csv_to_latex(input_file: str, output_file: str, column_indices: list):
    with open(input_file, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)
        selected_header = [header[i].replace('%', r'\%') for i in column_indices]
        selected_header = ["\\textbf{"+h+"}" for h in selected_header]
        indices_with_pct = [i for i, s in enumerate(selected_header) if '%' in s]
        rows = []
        for row in reader:
            selected_row = [row[i] for i in column_indices]
            rows.append(selected_row)

    # Generate LaTeX table
    with open(output_file, mode='w', encoding='utf-8') as texfile:
        texfile.write("\\begin{table}[h]\n")
        texfile.write("\\centering\n")
        texfile.write("\\renewcommand{\\arraystretch}{1.2}\n")
        texfile.write("\\setlength{\\tabcolsep}{2pt}\n")
        texfile.write("\\caption{\\label{table:summary_results_tmp} Summary of health check results by variant maker}\n")
        texfile.write("\\begin{tabular}{|" + " c |" * len(selected_header) + "}\n")
        texfile.write("\\hline\n")
        texfile.write(" & ".join(selected_header) + " \\\\ \hline\n")

        for row in rows:
            updated_row = []
            for i, col in enumerate(row):
                if i in indices_with_pct:
                    updated_row.append(f"{col}\%")
                else:
                    updated_row.append(col)
            texfile.write(" & ".join(updated_row) + " \\\\ \hline\n")

        texfile.write("\\end{tabular}\n")
        texfile.write("\\end{table}\n")


# Example usage:
csv_to_latex("I:\\InstruMate\\csv_to_latex\\experiment-summary.csv", "I:\\InstruMate\\csv_to_latex\\output.tex", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11])