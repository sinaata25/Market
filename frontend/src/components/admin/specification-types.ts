export type SpecificationKey = {
  id: number;
  name: string;
  slug: string;
  productCount?: number;
};

export type AdminProductSpecification = {
  keyId: number;
  name: string;
  slug: string;
  value: string;
  position: number;
};

export type SpecificationDraft = {
  clientId: string;
  key: SpecificationKey | null;
  value: string;
};

export type SpecificationDraftError = {
  key?: string;
  value?: string;
};

let nextDraftId = 0;

export function newSpecificationDraft(
  specification?: AdminProductSpecification
): SpecificationDraft {
  nextDraftId += 1;
  return {
    clientId: `specification-${nextDraftId}`,
    key: specification
      ? {
          id: specification.keyId,
          name: specification.name,
          slug: specification.slug,
        }
      : null,
    value: specification?.value ?? "",
  };
}

export function draftsFromProduct(
  specifications: AdminProductSpecification[] | undefined
): SpecificationDraft[] {
  return [...(specifications ?? [])]
    .sort((first, second) => first.position - second.position)
    .map(newSpecificationDraft);
}
