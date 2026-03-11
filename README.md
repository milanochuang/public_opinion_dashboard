# LLM-Based Political Judgement Classification

![Python](https://img.shields.io/badge/python-3.10-blue)
![NLP](https://img.shields.io/badge/task-NLP-green)
![LLM](https://img.shields.io/badge/model-GPT-orange)

Corpus annotation and large language model evaluation for detecting
evaluative judgement in political discourse.

This project was developed as a master's thesis in Computational
Linguistics at National Chengchi University.\
The repository contains a manually annotated political discourse dataset
and experiments evaluating GPT-based large language models for judgement
classification.

------------------------------------------------------------------------

# Project Highlights

-   Built a **political discourse corpus** from comments on PTT related
    to the 2024 Taiwan presidential election
-   Designed a **linguistic annotation framework based on Appraisal
    Theory**
-   Annotated evaluative language across **5 judgement categories**
-   Evaluated **GPT-based large language models** using zero-shot and
    few-shot prompting
-   Conducted **error analysis of LLM predictions**
-   Developed an **interactive visualization dashboard** for discourse
    exploration

------------------------------------------------------------------------

# Quick Demo

Example political comment:

    這個候選人看起來很有能力，但誠信真的很有問題。

Model output:

    Capacity: Positive
    Veracity: Negative

Target classification categories:

-   Normality
-   Capacity
-   Tenacity
-   Propriety
-   Veracity

Each label also includes **polarity (positive / negative)**.

------------------------------------------------------------------------

# Dataset

Source platform:

PTT -- Taiwan's largest online discussion forum.

Content:

-   political discussion threads
-   comments related to the 2024 Taiwan presidential election

Dataset properties:

-   manually annotated political comments
-   judgement category labels
-   polarity labels

Example annotation format:

  Comment              Category   Polarity
  -------------------- ---------- ----------
  這個候選人很有能力   Capacity   Positive
  他根本是在騙人       Veracity   Negative

------------------------------------------------------------------------

# Annotation Framework

The annotation scheme is based on **Appraisal Theory**, a linguistic
framework for analyzing evaluation in discourse.

Judgement subsystem categories:

  Category    Description
  ----------- ----------------------------------------
  Normality   whether a person is typical or unusual
  Capacity    competence and ability
  Tenacity    determination and reliability
  Propriety   ethical or moral evaluation
  Veracity    honesty and truthfulness

Each evaluative expression is annotated with:

-   judgement category
-   polarity

------------------------------------------------------------------------

# LLM Experiments

Large language models were evaluated for automated judgement
classification.

Model: OpenAI GPT

Prompting strategies tested:

-   zero-shot classification
-   few-shot classification

Example prompt:

    Classify the judgement expressed in the following political comment.

    Categories:
    Normality
    Capacity
    Tenacity
    Propriety
    Veracity

    Comment:
    這個政策根本是騙人的。

    Output format:
    Category + Polarity

Evaluation focuses on:

-   classification accuracy
-   category confusion patterns
-   qualitative error analysis

------------------------------------------------------------------------

# Key Challenges Identified

The experiments reveal several limitations in LLM interpretation of
political discourse:

-   sarcasm and irony
-   implicit evaluative language
-   ambiguous political expressions
-   context-dependent meaning

These findings highlight the challenges of applying LLMs to nuanced
political language.

------------------------------------------------------------------------

# Visualization Dashboard

An interactive dashboard was developed for corpus exploration.

Features:

-   judgement category distribution
-   polarity trends
-   time-based discourse patterns
-   word clouds of evaluative language

------------------------------------------------------------------------

# Repository Structure

    project/
    │
    ├── data/
    │   annotated_corpus
    │
    ├── annotation/
    │   annotation_guidelines
    │
    ├── prompts/
    │   classification_prompts
    │
    ├── experiments/
    │   llm_prompting_experiments
    │
    ├── analysis/
    │   corpus_statistics
    │
    ├── visualization/
    │   dashboard
    │
    └── README.md

------------------------------------------------------------------------

# Research Context

This project sits at the intersection of:

-   computational linguistics
-   discourse analysis
-   political communication
-   large language model evaluation

It demonstrates how linguistic theory and modern NLP methods can be
combined to analyze evaluative language in online political discourse.

------------------------------------------------------------------------

# Author

Master's Thesis\
Department of Computational Linguistics\
National Chengchi University

------------------------------------------------------------------------

# License

This project is intended for research and educational purposes.
