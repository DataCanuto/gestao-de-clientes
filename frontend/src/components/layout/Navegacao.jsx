// Menu lateral. A ordem segue o fluxo de trabalho: enviar -> conferir -> consultar -> exportar.

const ITENS_MENU = [
  { caminho: '/', rotulo: 'Painel', icone: '◧' },
  { caminho: '/enviar', rotulo: 'Enviar arquivos', icone: '⇪' },
  { caminho: '/lotes', rotulo: 'Lotes enviados', icone: '☰' },
  { caminho: '/clientes', rotulo: 'Clientes', icone: '◉' },
  { caminho: '/documentos', rotulo: 'Documentos', icone: '▤' },
  { caminho: '/exportar', rotulo: 'Exportar e organizar', icone: '⇩' },
]

export function Navegacao({ rota, aberta, aoFechar }) {
  const ativo = (caminho) => (caminho === '/' ? rota === '/' : rota === caminho || rota.startsWith(`${caminho}/`) || rota.startsWith(`${caminho}?`))
  return (
    <nav className={`menu ${aberta ? 'menu--aberto' : ''}`} aria-label="Menu principal">
      <div className="menu__marca">
        <span className="menu__logo" aria-hidden="true">A</span>
        <div>
          <strong>Gestão de Clientes</strong>
          <small>Gestão de documentos</small>
        </div>
      </div>
      <ul>
        {ITENS_MENU.map((item) => (
          <li key={item.caminho}>
            <a
              href={`#${item.caminho}`}
              className={`menu__item ${ativo(item.caminho) ? 'menu__item--ativo' : ''}`}
              aria-current={ativo(item.caminho) ? 'page' : undefined}
              onClick={aoFechar}
            >
              <span aria-hidden="true">{item.icone}</span> {item.rotulo}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
