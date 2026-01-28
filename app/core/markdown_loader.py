from pathlib import Path
from typing import Optional
from app.models.documents import DocumentMetadata, DocumentContent


class MarkdownLoader:
    def __init__(self):
        self.knowledge_dir = Path("/app/knowledge")

    def get_document(self, category: str, domain: str, filename: str) -> Optional[DocumentContent]:
        file_path = self.knowledge_dir / category / domain / f"{filename}.md"

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            metadata = DocumentMetadata(
                title=filename.replace("_", " ").title(),
                path=str(file_path),
                category=category,
                domain=domain,
                filename=filename
            )

            return DocumentContent(
                metadata=metadata,
                content=content,
                word_count=len(content.split())
            )
        except Exception as e:
            return None

    def list_documents(self, category: Optional[str] = None, 
                      domain: Optional[str] = None) -> list[DocumentMetadata]:
        documents = []

        categories = [category] if category else ["conventional", "islami"]
        domains = [domain] if domain else ["credit", "deposits"]

        for cat in categories:
            cat_path = self.knowledge_dir / cat
            if not cat_path.exists():
                continue

            for dom in domains:
                dom_path = cat_path / dom
                if not dom_path.exists():
                    continue

                for md_file in dom_path.glob("*.md"):
                    metadata = DocumentMetadata(
                        title=md_file.stem.replace("_", " ").title(),
                        path=str(md_file),
                        category=cat,
                        domain=dom,
                        filename=md_file.stem
                    )
                    documents.append(metadata)

        return documents

    def get_category_documents(self, category: str) -> list[DocumentMetadata]:
        return self.list_documents(category=category)

    def get_domain_documents(self, domain: str) -> list[DocumentMetadata]:
        return self.list_documents(domain=domain)

    def search_document_title(self, search_term: str) -> list[DocumentMetadata]:
        all_docs = self.list_documents()
        search_term_lower = search_term.lower()

        return [
            doc for doc in all_docs
            if search_term_lower in doc.filename.lower() or
               search_term_lower in doc.title.lower()
        ]

    def get_all_documents(self) -> list[DocumentMetadata]:
        return self.list_documents()

    def get_document_by_path(self, relative_path: str) -> Optional[DocumentContent]:
        file_path = self.knowledge_dir / relative_path

        if not file_path.exists() or not file_path.suffix == ".md":
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            parts = relative_path.split("/")
            category = parts[0] if len(parts) > 0 else "unknown"
            domain = parts[1] if len(parts) > 1 else "unknown"
            filename = parts[-1].replace(".md", "") if len(parts) > 0 else "unknown"

            metadata = DocumentMetadata(
                title=filename.replace("_", " ").title(),
                path=str(file_path),
                category=category,
                domain=domain,
                filename=filename
            )

            return DocumentContent(
                metadata=metadata,
                content=content,
                word_count=len(content.split())
            )
        except Exception as e:
            return None

    def extract_sections(self, content: str) -> dict[str, str]:
        sections = {}
        current_section = "introduction"
        current_text = []

        for line in content.split("\n"):
            if line.startswith("#"):
                if current_text:
                    sections[current_section] = "\n".join(current_text).strip()
                current_section = line.lstrip("#").strip().lower().replace(" ", "_")
                current_text = []
            else:
                current_text.append(line)

        if current_text:
            sections[current_section] = "\n".join(current_text).strip()

        return sections

    def get_document_summary(self, category: str, domain: str, filename: str) -> Optional[dict]:
        doc = self.get_document(category, domain, filename)

        if not doc:
            return None

        sections = self.extract_sections(doc.content)
        first_paragraph = next(
            (v for k, v in sections.items() if k != "introduction" and len(v) > 0),
            sections.get("introduction", "")
        )

        summary_text = first_paragraph[:200] + "..." if len(first_paragraph) > 200 else first_paragraph

        return {
            "title": doc.metadata.title,
            "category": doc.metadata.category,
            "domain": doc.metadata.domain,
            "summary": summary_text,
            "word_count": doc.word_count,
            "sections": list(sections.keys()),
            "path": doc.metadata.path
        }
