"""
Callbacks для системы справки и помощи.
"""

from dash import Input, Output, State, callback_context, html

try:
    from components.help_system import create_all_tooltips, create_help_button, create_help_modal
except ImportError:
    from web_interface.components.help_system import create_all_tooltips, create_help_button, create_help_modal


def register_help_callbacks(app):
    """
    Зарегистрировать callbacks для системы справки.

    Args:
        app: Dash приложение
    """

    # Инициализация системы справки при загрузке страницы
    @app.callback(
        Output("help-button-container", "children"),
        Output("help-system-container", "children"),
        Input("help-btn", "n_clicks"),
        Input("interval-component", "n_intervals"),
        prevent_initial_call=False,
    )
    def setup_help_system(_n_clicks, _n_intervals):
        """Инициализация системы справки."""
        help_button = create_help_button()
        help_modal = create_help_modal()
        tooltips = create_all_tooltips()

        return help_button, html.Div([help_modal, *tooltips])

    # Callback для открытия/закрытия модального окна справки
    @app.callback(
        Output("help-modal", "is_open"),
        [
            Input("help-btn", "n_clicks"),
            Input("close-help-modal", "n_clicks"),
            Input("close-help-modal-footer", "n_clicks"),
        ],
        [State("help-modal", "is_open")],
    )
    def toggle_help_modal(open_clicks, close_clicks_header, close_clicks_footer, is_open):
        """Открыть/закрыть модальное окно справки."""
        ctx = callback_context
        if not ctx.triggered:
            return False

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "help-btn":
            return True
        elif trigger_id in ["close-help-modal", "close-help-modal-footer"]:
            return False

        return is_open
