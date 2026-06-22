"""Pre-loaded demo data for the /demo page."""

DEMO_RESUME_TEXT = """
ALEX CHEN
San Francisco, CA | alex@email.com | github.com/alexchen | linkedin.com/in/alexchen

PROFESSIONAL SUMMARY
Senior Backend Engineer with 7 years building distributed systems at scale.
Led migration of monolithic payment platform to event-driven microservices
processing $2.3B annually. Specialized in high-throughput data pipelines,
real-time processing, and system reliability.

EXPERIENCE

Stripe
Senior Software Engineer
Jan 2021 - Present
- Architected event-driven payment reconciliation system handling 4M+ transactions daily with 99.99% accuracy, reducing reconciliation time from 48 hours to 12 minutes
- Led team of 6 engineers to rebuild the merchant onboarding pipeline, reducing activation time from 5 days to 4 hours and increasing conversion by 23%
- Designed and deployed distributed rate limiting service using Redis Cluster and token bucket algorithm, protecting 200+ API endpoints serving 50K+ requests/second
- Pioneered chaos engineering practice across the payments org, building custom fault injection framework that identified 14 critical failure modes before production impact

Uber
Software Engineer II
Mar 2019 - Dec 2021
- Built real-time driver matching optimization service in Go, reducing average pickup time by 18% across 3 major markets
- Implemented distributed tracing across 40+ microservices using Jaeger, reducing mean time to root cause from 4 hours to 20 minutes
- Developed automated data pipeline processing 2TB daily ride data for ML model training, reducing data freshness latency from 24h to 2h
- Contributed to open-source Go HTTP client library with 800+ GitHub stars

Amazon
Software Development Engineer
Jun 2017 - Feb 2019
- Built inventory forecasting service for AWS Marketplace processing predictions for 500K+ SKUs daily using Python and DynamoDB
- Reduced API latency by 40% through query optimization and caching layer design, improving p99 from 850ms to 510ms
- Developed automated testing framework for distributed systems that caught 23 regression bugs in pre-production

EDUCATION
MS Computer Science — Stanford University (2017)
BS Computer Science — UC Berkeley (2015)

SKILLS
Languages: Python, Go, Java, TypeScript
Databases: PostgreSQL, DynamoDB, Redis, Cassandra
Infrastructure: AWS, Kubernetes, Docker, Terraform
Frameworks: FastAPI, gRPC, Kafka, Apache Spark
Practices: System Design, Distributed Systems, Event-Driven Architecture, Chaos Engineering, CI/CD
""".strip()

DEMO_JD_TEXT = """
Senior Software Engineer, Backend — Google Cloud Platform

About the role:
We're looking for a Senior Software Engineer to join Google Cloud Platform's
infrastructure team. You'll design and build large-scale distributed systems
that power GCP's core services, serving millions of developers worldwide.

Responsibilities:
- Design and implement highly available, fault-tolerant distributed systems
- Lead technical design reviews and mentor junior engineers
- Optimize system performance at massive scale (millions of QPS)
- Collaborate with product managers and SRE teams to define reliability targets
- Contribute to system architecture decisions that impact GCP's roadmap

Requirements:
- BS/MS in Computer Science or equivalent practical experience
- 5+ years of software engineering experience with distributed systems
- Strong proficiency in Go, Java, or C++
- Experience with large-scale data processing (Kafka, Spark, or equivalent)
- Deep understanding of system design, networking, and storage systems
- Experience with cloud infrastructure (AWS, GCP, or Azure)

Preferred:
- Experience at a high-growth technology company
- Open source contributions
- Experience with Kubernetes and container orchestration
- Familiarity with chaos engineering and reliability testing
- MS or PhD in Computer Science

Compensation: $185,000 - $280,000 + equity + benefits
Location: Mountain View, CA (Hybrid)
""".strip()
