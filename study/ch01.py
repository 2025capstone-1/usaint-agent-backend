# https://wikidocs.net/233346

from datetime import datetime
import langchain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain_openai import ChatOpenAI

import lib.env


def get_today(_: None):
    return datetime.today().strftime("%b-%d")


def main():
    print(f"LangChain 버전: {langchain.__version__}")

    # ex1
    prompt = PromptTemplate.from_template("{num}의 10배는?")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    output_parser = StrOutputParser()

    # - chain1
    chain = prompt | llm | output_parser
    result = chain.invoke({"num": 5})
    print(f"chain1: {result}")

    # - chain2
    chain = RunnablePassthrough() | prompt | llm | output_parser
    result = chain.invoke({"num": 10})
    print(f"chain2: {result}")

    # ex2
    # - chain1
    chain1 = (
        {"country": RunnablePassthrough()}
        | PromptTemplate.from_template("{country}의 수도는?")
        | llm
        | output_parser
    )

    # - chain2
    chain2 = (
        {"country": RunnablePassthrough()}
        | PromptTemplate.from_template("{country}의 면적은?")
        | llm
        | output_parser
    )

    combined_chain = RunnableParallel(capital=chain1, area=chain2)
    print(combined_chain.invoke("대한민국"))

    # ex3
    chain = (
        {
            "today": RunnableLambda(get_today),
            "n": RunnablePassthrough(),
        }
        | PromptTemplate.from_template(
            "{today}에 발생한 역사적 사건 {n}개를 나열하세요. 연도를 표기해주세요."
        )
        | llm
        | output_parser
    )
    print(chain.invoke(3))


if __name__ == "__main__":
    main()
