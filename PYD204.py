# TODO
# 2. 設計說明：
# 請使用選擇敘述撰寫一程式，讓使用者輸入兩個整數a、b，然後再輸入一算術運算子 (+、-、*、/、//、%） ，輸出經過運算後的結果。

# 3. 輸入輸出：
# 輸入說明
# 兩個整數a、b，及一個算術運算子 (+、-、*、/、//、%）

a = int(input())
b = int(input())
c = input()

if c == '+':
    result = a + b
elif c == '-':
    result = a - b
elif c == '*':
    result = a * b
elif c == '/':
    result = a / b
elif c == '//':
    result = a // b
else:
    result = a % b

print(result)