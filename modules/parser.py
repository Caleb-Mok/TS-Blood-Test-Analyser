from modules.normalizer import Normalizer

class PDFParser:
    def parse(self, filepath):
        # return dict of extracted {param_name: value}
        self.normalizer = Normalizer()

        # get pre-normalized dict from filepath
        pre_dict = {}

        param_autos = self.normalizer.normalize(pre_dict)
       
        print("Parsing")
        return param_autos