"""
Enhanced AI Knowledge Ontology with deeper subtopics for dynamic unlocking
"""

ENHANCED_AI_ONTOLOGY = {
    "name": "Artificial Intelligence",
    "description": "The study and development of computer systems able to perform tasks that typically require human intelligence",
    "difficulty_min": 1,
    "difficulty_max": 10,
    "children": [
        {
            "name": "Foundations of AI",
            "description": "Core concepts and history of artificial intelligence",
            "difficulty_min": 1,
            "difficulty_max": 4,
            "children": [
                {
                    "name": "History of AI",
                    "description": "Evolution of AI from Turing to modern times",
                    "difficulty_min": 1,
                    "difficulty_max": 2,
                    "children": [
                        {
                            "name": "Early AI Pioneers",
                            "description": "Alan Turing, John McCarthy, and early AI researchers",
                            "difficulty_min": 2,
                            "difficulty_max": 3,
                        },
                        {
                            "name": "AI Winters and Revivals",
                            "description": "Periods of reduced funding and renewed interest in AI",
                            "difficulty_min": 3,
                            "difficulty_max": 4,
                        }
                    ]
                },
                {
                    "name": "Types of AI",
                    "description": "Narrow AI, General AI, and Superintelligence",
                    "difficulty_min": 1,
                    "difficulty_max": 3,
                    "children": [
                        {
                            "name": "Narrow AI Applications",
                            "description": "Current AI systems focused on specific tasks",
                            "difficulty_min": 2,
                            "difficulty_max": 4,
                        },
                        {
                            "name": "AGI Research",
                            "description": "Artificial General Intelligence development",
                            "difficulty_min": 6,
                            "difficulty_max": 9,
                        }
                    ]
                },
                {
                    "name": "AI Ethics and Safety",
                    "description": "Ethical considerations and safety in AI development",
                    "difficulty_min": 2,
                    "difficulty_max": 4,
                    "children": [
                        {
                            "name": "Algorithmic Bias",
                            "description": "Understanding and mitigating bias in AI systems",
                            "difficulty_min": 3,
                            "difficulty_max": 6,
                        },
                        {
                            "name": "AI Alignment",
                            "description": "Ensuring AI systems align with human values",
                            "difficulty_min": 5,
                            "difficulty_max": 8,
                        },
                        {
                            "name": "Explainable AI",
                            "description": "Making AI decisions interpretable and transparent",
                            "difficulty_min": 4,
                            "difficulty_max": 7,
                        }
                    ]
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
                            "children": [
                                {
                                    "name": "Logistic Regression",
                                    "description": "Linear approach to classification problems",
                                    "difficulty_min": 3,
                                    "difficulty_max": 5,
                                },
                                {
                                    "name": "Decision Trees",
                                    "description": "Tree-based classification algorithms",
                                    "difficulty_min": 3,
                                    "difficulty_max": 6,
                                },
                                {
                                    "name": "Support Vector Machines",
                                    "description": "Maximum margin classification",
                                    "difficulty_min": 5,
                                    "difficulty_max": 7,
                                },
                                {
                                    "name": "Ensemble Methods",
                                    "description": "Random Forest, Gradient Boosting, etc.",
                                    "difficulty_min": 5,
                                    "difficulty_max": 8,
                                }
                            ]
                        },
                        {
                            "name": "Regression",
                            "description": "Predicting continuous values",
                            "difficulty_min": 2,
                            "difficulty_max": 5,
                            "children": [
                                {
                                    "name": "Linear Regression",
                                    "description": "Fundamental regression technique",
                                    "difficulty_min": 2,
                                    "difficulty_max": 4,
                                },
                                {
                                    "name": "Polynomial Regression",
                                    "description": "Non-linear relationships with polynomials",
                                    "difficulty_min": 3,
                                    "difficulty_max": 5,
                                },
                                {
                                    "name": "Regularization Techniques",
                                    "description": "Ridge, Lasso, and Elastic Net regression",
                                    "difficulty_min": 4,
                                    "difficulty_max": 6,
                                }
                            ]
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
                            "children": [
                                {
                                    "name": "K-Means Clustering",
                                    "description": "Centroid-based clustering algorithm",
                                    "difficulty_min": 3,
                                    "difficulty_max": 5,
                                },
                                {
                                    "name": "Hierarchical Clustering",
                                    "description": "Tree-based clustering approaches",
                                    "difficulty_min": 4,
                                    "difficulty_max": 6,
                                },
                                {
                                    "name": "DBSCAN",
                                    "description": "Density-based clustering",
                                    "difficulty_min": 5,
                                    "difficulty_max": 7,
                                }
                            ]
                        },
                        {
                            "name": "Dimensionality Reduction",
                            "description": "Reducing feature space",
                            "difficulty_min": 4,
                            "difficulty_max": 7,
                            "children": [
                                {
                                    "name": "Principal Component Analysis",
                                    "description": "Linear dimensionality reduction technique",
                                    "difficulty_min": 4,
                                    "difficulty_max": 6,
                                },
                                {
                                    "name": "t-SNE",
                                    "description": "Non-linear dimensionality reduction for visualization",
                                    "difficulty_min": 5,
                                    "difficulty_max": 7,
                                },
                                {
                                    "name": "UMAP",
                                    "description": "Uniform Manifold Approximation and Projection",
                                    "difficulty_min": 6,
                                    "difficulty_max": 8,
                                }
                            ]
                        }
                    ]
                },
                {
                    "name": "Reinforcement Learning",
                    "description": "Learning through interaction and rewards",
                    "difficulty_min": 4,
                    "difficulty_max": 9,
                    "children": [
                        {
                            "name": "Q-Learning",
                            "description": "Value-based reinforcement learning",
                            "difficulty_min": 5,
                            "difficulty_max": 7,
                        },
                        {
                            "name": "Policy Gradient Methods",
                            "description": "Direct policy optimization",
                            "difficulty_min": 6,
                            "difficulty_max": 8,
                        },
                        {
                            "name": "Deep Reinforcement Learning",
                            "description": "Combining deep learning with RL",
                            "difficulty_min": 7,
                            "difficulty_max": 9,
                        }
                    ]
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
                    "children": [
                        {
                            "name": "Perceptron",
                            "description": "Single layer neural network",
                            "difficulty_min": 3,
                            "difficulty_max": 4,
                        },
                        {
                            "name": "Backpropagation",
                            "description": "Training algorithm for neural networks",
                            "difficulty_min": 4,
                            "difficulty_max": 6,
                        },
                        {
                            "name": "Activation Functions",
                            "description": "ReLU, Sigmoid, Tanh, and others",
                            "difficulty_min": 3,
                            "difficulty_max": 5,
                        }
                    ]
                },
                {
                    "name": "Convolutional Neural Networks",
                    "description": "Networks for image processing",
                    "difficulty_min": 5,
                    "difficulty_max": 8,
                    "children": [
                        {
                            "name": "CNN Architectures",
                            "description": "LeNet, AlexNet, VGG, ResNet",
                            "difficulty_min": 6,
                            "difficulty_max": 8,
                        },
                        {
                            "name": "Transfer Learning",
                            "description": "Using pre-trained models",
                            "difficulty_min": 5,
                            "difficulty_max": 7,
                        }
                    ]
                },
                {
                    "name": "Recurrent Neural Networks",
                    "description": "Networks for sequential data",
                    "difficulty_min": 5,
                    "difficulty_max": 8,
                    "children": [
                        {
                            "name": "LSTM",
                            "description": "Long Short-Term Memory networks",
                            "difficulty_min": 6,
                            "difficulty_max": 8,
                        },
                        {
                            "name": "GRU",
                            "description": "Gated Recurrent Units",
                            "difficulty_min": 6,
                            "difficulty_max": 7,
                        }
                    ]
                },
                {
                    "name": "Transformers",
                    "description": "Attention-based architectures",
                    "difficulty_min": 6,
                    "difficulty_max": 9,
                    "children": [
                        {
                            "name": "Attention Mechanism",
                            "description": "Self-attention and multi-head attention",
                            "difficulty_min": 6,
                            "difficulty_max": 8,
                        },
                        {
                            "name": "Vision Transformers",
                            "description": "Transformers for computer vision",
                            "difficulty_min": 7,
                            "difficulty_max": 9,
                        }
                    ]
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
                    "children": [
                        {
                            "name": "Tokenization",
                            "description": "Breaking text into tokens",
                            "difficulty_min": 2,
                            "difficulty_max": 3,
                        },
                        {
                            "name": "Text Normalization",
                            "description": "Stemming, lemmatization, and cleaning",
                            "difficulty_min": 3,
                            "difficulty_max": 4,
                        }
                    ]
                },
                {
                    "name": "Traditional NLP",
                    "description": "Statistical and rule-based approaches",
                    "difficulty_min": 3,
                    "difficulty_max": 6,
                    "children": [
                        {
                            "name": "N-gram Models",
                            "description": "Statistical language modeling",
                            "difficulty_min": 3,
                            "difficulty_max": 5,
                        },
                        {
                            "name": "Named Entity Recognition",
                            "description": "Identifying entities in text",
                            "difficulty_min": 4,
                            "difficulty_max": 6,
                        }
                    ]
                },
                {
                    "name": "Large Language Models",
                    "description": "GPT, BERT, and modern language models",
                    "difficulty_min": 6,
                    "difficulty_max": 9,
                    "children": [
                        {
                            "name": "BERT and Variants",
                            "description": "Bidirectional encoder representations",
                            "difficulty_min": 6,
                            "difficulty_max": 8,
                        },
                        {
                            "name": "GPT Family",
                            "description": "Generative Pre-trained Transformers",
                            "difficulty_min": 6,
                            "difficulty_max": 8,
                        },
                        {
                            "name": "Prompt Engineering",
                            "description": "Optimizing prompts for LLMs",
                            "difficulty_min": 5,
                            "difficulty_max": 7,
                        },
                        {
                            "name": "Fine-tuning LLMs",
                            "description": "Adapting models to specific tasks",
                            "difficulty_min": 7,
                            "difficulty_max": 9,
                        }
                    ]
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
                    "children": [
                        {
                            "name": "Image Preprocessing",
                            "description": "Data augmentation and normalization",
                            "difficulty_min": 3,
                            "difficulty_max": 5,
                        },
                        {
                            "name": "Multi-class Classification",
                            "description": "Classifying images into multiple categories",
                            "difficulty_min": 4,
                            "difficulty_max": 6,
                        }
                    ]
                },
                {
                    "name": "Object Detection",
                    "description": "Locating objects in images",
                    "difficulty_min": 5,
                    "difficulty_max": 8,
                    "children": [
                        {
                            "name": "YOLO",
                            "description": "You Only Look Once object detection",
                            "difficulty_min": 6,
                            "difficulty_max": 8,
                        },
                        {
                            "name": "R-CNN Family",
                            "description": "Region-based convolutional networks",
                            "difficulty_min": 6,
                            "difficulty_max": 8,
                        }
                    ]
                },
                {
                    "name": "Image Segmentation",
                    "description": "Pixel-level image understanding",
                    "difficulty_min": 6,
                    "difficulty_max": 9,
                    "children": [
                        {
                            "name": "Semantic Segmentation",
                            "description": "Pixel-wise classification",
                            "difficulty_min": 6,
                            "difficulty_max": 8,
                        },
                        {
                            "name": "Instance Segmentation",
                            "description": "Distinguishing object instances",
                            "difficulty_min": 7,
                            "difficulty_max": 9,
                        }
                    ]
                }
            ]
        }
    ]
}

# Enhanced prerequisites mapping
ENHANCED_PREREQUISITES = {
    # Base prerequisites
    "Machine Learning": ["Foundations of AI"],
    "Deep Learning": ["Machine Learning"],
    "Natural Language Processing": ["Machine Learning"],
    "Computer Vision": ["Deep Learning"],
    
    # Supervised Learning
    "Supervised Learning": ["Machine Learning"],
    "Classification": ["Supervised Learning"],
    "Regression": ["Supervised Learning"],
    
    # Classification subtopics
    "Logistic Regression": ["Classification"],
    "Decision Trees": ["Classification"],
    "Support Vector Machines": ["Classification", "Linear Regression"],
    "Ensemble Methods": ["Decision Trees", "Classification"],
    
    # Regression subtopics
    "Linear Regression": ["Regression"],
    "Polynomial Regression": ["Linear Regression"],
    "Regularization Techniques": ["Linear Regression"],
    
    # Unsupervised Learning
    "Unsupervised Learning": ["Supervised Learning"],
    "Clustering": ["Unsupervised Learning"],
    "Dimensionality Reduction": ["Unsupervised Learning"],
    
    # Clustering subtopics
    "K-Means Clustering": ["Clustering"],
    "Hierarchical Clustering": ["Clustering"],
    "DBSCAN": ["K-Means Clustering"],
    
    # Dimensionality Reduction subtopics
    "Principal Component Analysis": ["Dimensionality Reduction"],
    "t-SNE": ["Principal Component Analysis"],
    "UMAP": ["Principal Component Analysis"],
    
    # Reinforcement Learning
    "Reinforcement Learning": ["Machine Learning"],
    "Q-Learning": ["Reinforcement Learning"],
    "Policy Gradient Methods": ["Q-Learning"],
    "Deep Reinforcement Learning": ["Deep Learning", "Reinforcement Learning"],
    
    # Neural Networks
    "Neural Network Fundamentals": ["Supervised Learning"],
    "Perceptron": ["Neural Network Fundamentals"],
    "Backpropagation": ["Perceptron"],
    "Activation Functions": ["Neural Network Fundamentals"],
    
    # Deep Learning architectures
    "Convolutional Neural Networks": ["Neural Network Fundamentals"],
    "Recurrent Neural Networks": ["Neural Network Fundamentals"],
    "Transformers": ["Neural Network Fundamentals"],
    
    # CNN subtopics
    "CNN Architectures": ["Convolutional Neural Networks"],
    "Transfer Learning": ["Convolutional Neural Networks"],
    
    # RNN subtopics
    "LSTM": ["Recurrent Neural Networks"],
    "GRU": ["Recurrent Neural Networks"],
    
    # Transformer subtopics
    "Attention Mechanism": ["Transformers"],
    "Vision Transformers": ["Transformers", "Convolutional Neural Networks"],
    
    # NLP
    "Text Processing": ["Natural Language Processing"],
    "Traditional NLP": ["Text Processing"],
    "Large Language Models": ["Transformers", "Traditional NLP"],
    
    # NLP subtopics
    "Tokenization": ["Text Processing"],
    "Text Normalization": ["Tokenization"],
    "N-gram Models": ["Traditional NLP"],
    "Named Entity Recognition": ["Traditional NLP"],
    "BERT and Variants": ["Large Language Models"],
    "GPT Family": ["Large Language Models"],
    "Prompt Engineering": ["Large Language Models"],
    "Fine-tuning LLMs": ["Large Language Models"],
    
    # Computer Vision
    "Image Classification": ["Computer Vision"],
    "Object Detection": ["Image Classification"],
    "Image Segmentation": ["Object Detection"],
    
    # CV subtopics
    "Image Preprocessing": ["Image Classification"],
    "Multi-class Classification": ["Image Classification"],
    "YOLO": ["Object Detection"],
    "R-CNN Family": ["Object Detection"],
    "Semantic Segmentation": ["Image Segmentation"],
    "Instance Segmentation": ["Semantic Segmentation"],
    
    # Ethics and Safety
    "AI Ethics and Safety": ["Types of AI"],
    "Algorithmic Bias": ["AI Ethics and Safety"],
    "AI Alignment": ["AI Ethics and Safety"],
    "Explainable AI": ["AI Ethics and Safety"],
    
    # History
    "History of AI": ["Foundations of AI"],
    "Early AI Pioneers": ["History of AI"],
    "AI Winters and Revivals": ["History of AI"],
    
    # Types of AI
    "Types of AI": ["Foundations of AI"],
    "Narrow AI Applications": ["Types of AI"],
    "AGI Research": ["Types of AI", "Machine Learning"],
}