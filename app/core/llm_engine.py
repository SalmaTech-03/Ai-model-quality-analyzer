import pandas as pd
from evidently.report import Report
from evidently.descriptors import TextLength, Sentiment

class LLMEngine:
    """
    Audits Text Data for Quality and Sentiment.
    Used for the 'GenAI Guardrails' feature.
    """
    def scan_response(self, prompt: str, response: str):
        # Wrap data in a DataFrame for Evidently
        data = pd.DataFrame({"response": [response]})
        
        # Define metrics (Text Length & Sentiment)
        report = Report(metrics=[
            TextLength(column_name="response"),
            Sentiment(column_name="response")
        ])
        
        # Run analysis
        report.run(reference_data=None, current_data=data)
        
        # Return dictionary result
        return report.as_dict()