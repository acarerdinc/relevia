"""
AI Knowledge Ontology Data Structure
This will be used to seed the database with the AI topic hierarchy
"""

AI_ONTOLOGY = {
    "name": "Artificial Intelligence",
    "description": "The study and development of computer systems able to perform tasks that typically require human intelligence",
    "difficulty_min": 1,
    "difficulty_max": 10,
    "children": [
        {
            "name": "Foundations of AI",
            "description": "Core concepts and history of artificial intelligence",
            "difficulty_min": 1,
            "difficulty_max": 3,
            "children": [
                {
                    "name": "History of AI",
                    "description": "Evolution of AI from Turing to modern times",
                    "difficulty_min": 1,
                    "difficulty_max": 2,
                },
                {
                    "name": "Types of AI",
                    "description": "Narrow AI, General AI, and Superintelligence",
                    "difficulty_min": 1,
                    "difficulty_max": 3,
                },
                {
                    "name": "AI Ethics and Safety",
                    "description": "Ethical considerations and safety in AI development",
                    "difficulty_min": 2,
                    "difficulty_max": 4,
                }
            ]
        },
        {
            "name": "Machine Learning",
            "description": "Algorithms that improve through experience",
            "difficulty_min": 2,
            "difficulty_max": 8,
            "children": [
                {
                    "name": "Supervised Learning",
                    "description": "Learning from labeled data",
                    "difficulty_min": 2,
                    "difficulty_max": 6,
                    "children": [
                        {
                            "name": "Classification",
                            "description": "Predicting discrete categories",
                            "difficulty_min": 2,
                            "difficulty_max": 5,
                        },
                        {
                            "name": "Regression",
                            "description": "Predicting continuous values",
                            "difficulty_min": 2,
                            "difficulty_max": 5,
                        }
                    ]
                },
                {
                    "name": "Unsupervised Learning",
                    "description": "Finding patterns in unlabeled data",
                    "difficulty_min": 3,
                    "difficulty_max": 7,
                    "children": [
                        {
                            "name": "Clustering",
                            "description": "Grouping similar data points",
                            "difficulty_min": 3,
                            "difficulty_max": 6,
                        },
                        {
                            "name": "Dimensionality Reduction",
                            "description": "Reducing feature space",
                            "difficulty_min": 4,
                            "difficulty_max": 7,
                        }
                    ]
                },
                {
                    "name": "Reinforcement Learning",
                    "description": "Learning through interaction and rewards",
                    "difficulty_min": 4,
                    "difficulty_max": 8,
                }
            ]
        },
        {
            "name": "Deep Learning",
            "description": "Neural networks with multiple layers",
            "difficulty_min": 4,
            "difficulty_max": 9,
            "children": [
                {
                    "name": "Neural Network Fundamentals",
                    "description": "Basic building blocks of neural networks",
                    "difficulty_min": 3,
                    "difficulty_max": 6,
                },
                {
                    "name": "Convolutional Neural Networks",
                    "description": "Networks for image processing",
                    "difficulty_min": 5,
                    "difficulty_max": 8,
                },
                {
                    "name": "Recurrent Neural Networks",
                    "description": "Networks for sequential data",
                    "difficulty_min": 5,
                    "difficulty_max": 8,
                },
                {
                    "name": "Transformers",
                    "description": "Attention-based architectures",
                    "difficulty_min": 6,
                    "difficulty_max": 9,
                }
            ]
        },
        {
            "name": "Natural Language Processing",
            "description": "AI for understanding and generating human language",
            "difficulty_min": 3,
            "difficulty_max": 9,
            "children": [
                {
                    "name": "Text Processing",
                    "description": "Basic text manipulation and analysis",
                    "difficulty_min": 2,
                    "difficulty_max": 4,
                },
                {
                    "name": "Traditional NLP",
                    "description": "Statistical and rule-based approaches",
                    "difficulty_min": 3,
                    "difficulty_max": 6,
                },
                {
                    "name": "Large Language Models",
                    "description": "GPT, BERT, and modern language models",
                    "difficulty_min": 6,
                    "difficulty_max": 9,
                }
            ]
        },
        {
            "name": "Computer Vision",
            "description": "AI for interpreting visual information",
            "difficulty_min": 4,
            "difficulty_max": 9,
            "children": [
                {
                    "name": "Image Classification",
                    "description": "Categorizing images",
                    "difficulty_min": 4,
                    "difficulty_max": 7,
                },
                {
                    "name": "Object Detection",
                    "description": "Locating objects in images",
                    "difficulty_min": 5,
                    "difficulty_max": 8,
                },
                {
                    "name": "Image Segmentation",
                    "description": "Pixel-level image understanding",
                    "difficulty_min": 6,
                    "difficulty_max": 9,
                }
            ]
        }
    ]
}

# Prerequisites mapping (topic_name -> list of prerequisite topic names)
PREREQUISITES = {
    "Machine Learning": ["Foundations of AI"],
    "Deep Learning": ["Machine Learning", "Neural Network Fundamentals"],
    "Neural Network Fundamentals": ["Supervised Learning"],
    "Convolutional Neural Networks": ["Neural Network Fundamentals"],
    "Recurrent Neural Networks": ["Neural Network Fundamentals"],
    "Transformers": ["Neural Network Fundamentals", "Natural Language Processing"],
    "Large Language Models": ["Transformers", "Traditional NLP"],
    "Supervised Learning": ["Foundations of AI"],
    "Unsupervised Learning": ["Foundations of AI", "Supervised Learning"],
    "Reinforcement Learning": ["Supervised Learning", "Unsupervised Learning"],
    "Computer Vision": ["Deep Learning", "Convolutional Neural Networks"],
    "Object Detection": ["Image Classification"],
    "Image Segmentation": ["Object Detection"],
}