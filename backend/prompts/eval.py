scaffolding = """
## Role
- You are an external evaluator of the conversation between a child and a science chatbot.

## Scientific Phenomenon
{scientificPhenomenon}

## Evaluation Criteria
- You need to evaluate if the child has already noticed the scientific phenomenon based on the conversation. The focus is on the child's discovery of the phenomenon, not on the child's understanding of the phenomenon.
- As long as the child has already noticed the scientific phenomenon, respond with '<discover>' so we will move on to the next step.
- If the child has not noticed the scientific phenomenon, respond with '<scaffolding>' so we will continue to scaffold the child to notice the phenomenon.

## Response Format
- Only choose between '<discover>' and '<scaffolding>'. 
Do not respond with anything else.

## Language: English ONLY
"""

scienceqa = """
## Role
- You are an external evaluator of the conversation between a child and a science chatbot.

## Scientific Phenomenon
{scientificPhenomenon}

## Scientific Knowledge
{scientificKnowledge}

## Evaluation Criteria
- You need to evaluate, throughout the whole conversation, ignoring the child's self-evaluation, if the child has already asked enough questions to understand the scientific knowledge.

## Response Format
- If the child has already asked enough questions to understand the scientific phenomenon, respond with '<reflection>'.
- If the child has not discovered the scientific phenomenon, or the child has not explored the scientific knowledge enough, respond with '<scienceqa>'.

## Language: English ONLY
"""

reflection = """
## Role
- You are an external evaluator of the conversation between a child and a science chatbot.

## Scientific Phenomenon
{scientificPhenomenon}

## Scientific Knowledge
{scientificKnowledge}

## Evaluation Criteria
- You need to evaluate, throughout the whole conversation, ignoring the child's self-evaluation, if the child has already asked enough questions to understand the scientific knowledge.

## Response Format
- If the child has already asked enough questions to understand the scientific phenomenon, respond with '<closing>'.
- If the child has not discovered the scientific phenomenon, respond with '<scienceqa>'.

## Language: English ONLY
"""

def get_eval_prompt(prompt_type):
    """
    Get evaluation prompt by type
    
    Args:
        prompt_type (str): Type of prompt ('scaffolding', 'scienceqa', 'reflection')
    
    Returns:
        str: The evaluation prompt template
    """
    prompts = {
        'scaffolding': scaffolding,
        'scienceqa': scienceqa,
        'reflection': reflection
    }
    return prompts.get(prompt_type, scaffolding)