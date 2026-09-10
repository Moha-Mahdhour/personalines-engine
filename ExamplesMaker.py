import random
class ExampleMaker:
    
    def __init__(self) -> None:
        self.lines = []
        with open("examples.txt", "r") as f:
            for line in f:
                self.lines.append(line.replace("\n", ""))
                

    def get_examples(self, num: int):
        return random.sample(self.lines, num)
    
    def get_examples_string(self, num: int):
        examplesList = self.get_examples(num)
        random.shuffle(examplesList)
        
        examples = ""
        
        for line in examplesList:
            examples += "Example: " + line + "\n"
            
        return examples

        
        
        
if __name__ == "__main__":
    x = ExampleMaker()
    
    print(x.get_examples_string(5))