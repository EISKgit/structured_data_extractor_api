from pydantic import BaseModel, Field, create_model
from typing import Optional, Type, List, Dict, Any

#section 2
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence

import logging
logger = logging.getLogger(__name__)

load_dotenv()

# Dynamic pydantic model generator


def create_extraction_schema(field_string: str) -> Type[BaseModel]:
    """Dynamically creates a pydantic model from a comma-seperated string. """

    # clean the input fileds and normalize names for pydantic (snake_case)
    field_names = [name.strip() for name in field_string.split(',')]

    # A dictinory of fields for the dynamic model
    # key : field_name, value : (type, default/Filed)

    fields = {}

    for name in field_names:
        # lowercase_with_underscore for reliable pydantic filed names
        field_key = name.lower().replace(' ', '_').replace('-', '_')

        # This tells Pydantic and LLM the expected structure
        fields[field_key] = (Optional[str], Field(
            default=None,
            description=f"The extracted value for '{name}'. Set to null if the information is not present in the document."
        ))

    # create_model is a pydantic utility function
    #  The new class is given a specific name for clarity in the prompt/logs
    DynamicSchema = create_model(
        'DocumentDataSchema',
        **fields,
        __doc__="Schema for extracting structured data from a document."
    )
    return DynamicSchema


# Example usage (not run in the final API, just for illustration)
# MySchema = create_extraction_schema("Invoice ID, Customer Name, Total Amount")
# print(MySchema.schema_json(indent=1)) # shows the resulting JSON schema

# --------------- section 2 ----------------------------------

def run_extraction_chain(document_text: str, schema: Type[BaseModel]) -> Dict[str, Any]:
    """Runs the langchain pipeline for data extraction. """


    schema_name = schema.__name__ # Get the name of the dynamic schema
    
    logger.info(f"Initializing LangChain pipeline with schema: {schema_name}")

    # Initialize the LLM
    # Model that supports the structured output
    llm  = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.5,
)
    
    # Bind the pydantic schema to the LLM
    # it forces the model to return data that fits the Pydantic schema
    structured_llm = llm.with_structured_output(schema)

    # Define the prompt template 
    SYSTEM_TEMPLATE = (
        "You are an expert document data extraction specialist. "
        "Your task is to extract specific data points from the provided document text and return it as a JSON object that strictly adheres to the given schema. "
        "CRITICAL RULE: If a requested data point is NOT found in the document, you MUST set its value to null (None in Python). DO NOT MAKE UP DATA."
    )


    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_TEMPLATE),
        ("human", "DOCUMENT TEXT: \n---\n{document_text}\n---\n")
    ])

    # chain
    chain = prompt | structured_llm

    # Invoke the Chain
    logger.debug(f"Invoking LLM for structured output...")

    # Invoke chain
    result_model = chain.invoke({"document_text": document_text})
    logger.debug(f"LLM call finished. Received Pydantic model instance.")

    # Convert the Pydantic Model instance to a dictionary for the DRF response
    return result_model.model_dump()