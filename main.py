import tkinter
import math

class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero.")
        return a / b

class Deziner:
    def __init__(self, master):
        self.master = master
        master.title("Calculator")

        self.result_var = tkinter.StringVar()

        self.result_entry = tkinter.Entry(master, textvariable=self.result_var)
        self.result_entry.grid(row=0, column=0, columnspan=4)

        self.create_buttons()

    def create_buttons(self):
        buttons = [
            ('7', 1, 0), ('8', 1, 1), ('9', 1, 2), ('/', 1, 3),
            ('4', 2, 0), ('5', 2, 1), ('6', 2, 2), ('*', 2, 3),
            ('1', 3, 0), ('2', 3, 1), ('3', 3, 2), ('-', 3, 3),
            ('0', 4, 0), ('.', 4, 1), ('+', 4, 2), ('=', 4, 3),
        ]

        for (text, row, col) in buttons:
            button = tkinter.Button(self.master, text=text,
                                    command=lambda t=text: self.on_button_click(t))
            button.grid(row=row, column=col)

    def on_button_click(self, char):
        if char == '=':
            try:
                expression = self.result_var.get()
                result = eval(expression)
                self.result_var.set(result)
            except Exception as e:
                self.result_var.set("Error")
        else:
            current_text = self.result_var.get()
            new_text = current_text + char
            self.result_var.set(new_text)

if __name__ == "__main__":
    root = tkinter.Tk()
    deziner = Deziner(root)
    root.mainloop()

class Math:
    @staticmethod
    def square_root(x):
        if x < 0:
            raise ValueError("Cannot take the square root of a negative number.")
        return math.sqrt(x)

    @staticmethod
    def power(base, exponent):
        return math.pow(base, exponent)

class Connector:
    def __init__(self, calculator):
        self.calculator = calculator

    def perform_operation(self, operation, a, b):
        if operation == 'add':
            return self.calculator.add(a, b)
        elif operation == 'subtract':
            return self.calculator.subtract(a, b)
        elif operation == 'multiply':
            return self.calculator.multiply(a, b)
        elif operation == 'divide':
            return self.calculator.divide(a, b)
        else:
            raise ValueError("Invalid operation.")