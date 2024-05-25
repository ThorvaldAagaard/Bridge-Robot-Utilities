import pandas as pd

df1 = pd.read_csv('Random B1-256-GIB.csv')
print("The dataframe is:")
print(df1)
html_string = df1.to_html()
print("The html string is:")
print(html_string)