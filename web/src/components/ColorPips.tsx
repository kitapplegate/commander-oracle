export function ColorPips({ colors }: { colors: string[] }) {
  const list = colors.length ? colors : ['C']
  return (
    <span className="pips">
      {list.map(c => (
        <img key={c} src={`https://svgs.scryfall.io/card-symbols/${c}.svg`} alt={c} width={16} height={16} />
      ))}
    </span>
  )
}
