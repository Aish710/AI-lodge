// Display wording only. Historical API fields and persisted evidence stay intact.
// This substitution changes no figures, identifiers, units or budget scope.
export const costTerms = text => typeof text === 'string'
  ? text.replace(/\btrue[ -]cost\b/gi, match => /^[A-Z]/.test(match) ? 'Generalised cost' : 'generalised cost')
  : text
