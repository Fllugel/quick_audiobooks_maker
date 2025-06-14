import gradio as gr

class UILayout:
    def __init__(self, ui):
        self.ui = ui
    
    def create_ui(self):
        """Create the Gradio interface."""
        with gr.Blocks(title="Kokoro Audiobook Generator", css="""
            .gradio-container {
                max-width: 100% !important;
                padding: 0 !important;
                min-height: 100vh !important;
                display: flex !important;
                flex-direction: column !important;
                overflow-y: auto !important; /* Enable vertical scrolling */
            }
            /* Target the title area more specifically */
            .gradio-container > div:first-child,
            .gradio-container > div:first-child > div,
            .gradio-container > div:first-child > div > div {
                overflow: visible !important;
                max-height: fit-content !important;
            }
            .gradio-container h1 {
                margin: 0 !important;
                padding: 10px 0 !important;
                white-space: nowrap !important;
            }
            /* Remove any potential scrollbars from markdown elements */
            .gradio-container .markdown {
                overflow: visible !important;
                max-height: fit-content !important;
            }
            .main-content-column {
                flex-grow: 1 !important;
                display: flex !important;
                flex-direction: column !important;
                min-height: 0;
                height: auto !important; /* Allow content to expand */
                overflow: visible !important;
            }
            .tabs {
                flex-grow: 1 !important;
                display: flex !important;
                flex-direction: column !important;
                min-height: 0;
                height: auto !important;
                overflow: visible !important;
            }
            /* Targeting Gradio's internal tab panel content area */
            .tabs > div[data-testid*="panel"] {
                flex-grow: 1 !important;
                display: flex !important;
                flex-direction: column !important;
                min-height: 0;
                height: auto !important;
                overflow: visible !important;
            }
            .tab-panel-content-column {
                flex-grow: 1 !important;
                display: flex !important;
                flex-direction: column !important;
                min-height: 0;
                height: auto !important;
                overflow: visible !important;
            }
            .raw-text-panel-content {
                flex-grow: 1 !important;
                display: flex !important;
                flex-direction: column !important;
                min-height: 0;
                height: auto !important;
                overflow: visible !important;
            }
            /* Targeting Gradio's internal tab item content */
            .gradio-tabitem {
                flex-grow: 1 !important;
                height: auto !important;
                padding: 0 !important;
                display: flex !important;
                flex-direction: column !important;
                overflow: visible !important;
            }
            .sections-container,
            .raw-text-container {
                flex-grow: 1 !important;
                display: flex !important;
                flex-direction: column !important;
                min-height: 0;
                height: auto !important;
                overflow: visible !important;
            }
            /* Targeting Gradio's internal dataframe element */
            .gradio-dataframe {
                flex-grow: 1 !important;
                height: auto !important;
                overflow-y: auto !important;
                display: flex !important;
                flex-direction: column !important;
            }
            .gradio-dataframe > div {
                flex-grow: 1 !important;
                height: auto !important;
                display: flex !important;
                flex-direction: column !important;
                overflow: visible !important;
            }
            .gradio-dataframe table {
                flex-grow: 1 !important;
                height: auto !important;
            }
            .sections-container .gradio-dataframe table td {
                white-space: normal !important; /* Enable text wrapping in Dataframe cells */
            }
            .sections-container textarea,
            .raw-text-container textarea {
                flex-grow: 1 !important;
                overflow-y: auto !important;
                height: calc(80vh * 0.8) !important; /* 20% smaller than 80vh */
                min-height: unset !important; 
            }
            .sections-container label,
            .raw-text-container label {
                min-height: 24px !important;
                display: block !important;
                margin-bottom: 4px !important;
                width: 100% !important;
            }
            .sections-container .checkbox-group {
                display: flex !important;
                flex-direction: column !important;
            }
            .tab-nav {
                margin-bottom: 20px !important;
            }
            .sections-container .gradio-dataframe {
                flex-grow: 1 !important;
                height: 80vh !important;
                overflow-y: auto !important;
                min-height: unset !important; 
            }
            /* hide any horizontal overflow site‑wide */
            body, .gradio-container {
                overflow-x: hidden !important;
            }
            /* make sure the title block itself can't overflow */
            .gradio-container h1 {
                box-sizing: border-box !important;
                width: 100% !important;        /* never wider than its parent */
                max-width: 100vw !important;   /* never wider than the viewport */
                overflow-x: hidden !important; /* hide any stray overflow */
                text-overflow: ellipsis !important;
                white-space: nowrap !important;
            }
            /* 1) Kill all utility overflow classes */
            .overflow-auto,
            .overflow-x-auto,
            .overflow-scroll,
            .overflow-x-scroll {
                overflow: hidden !important;
            }
            /* 2) Make absolutely sure the header container can't scroll */
            .gradio-container section > header,
            .gradio-container section > header > div {
                overflow-x: hidden !important;
                overflow-y: hidden !important;
            }
            /* 3) Clamp the Markdown wrapper that renders your H1 */
            .gradio-container .markdown h1,
            .gradio-container .markdown:first-of-type {
                box-sizing: border-box !important;
                width: 100% !important;
                max-width: 100vw !important;
                overflow: hidden !important;
                white-space: nowrap !important;
                text-overflow: ellipsis !important;
            }
            /* Ensure the page itself never scrolls horizontally */
            html, body {
                overflow-x: hidden !important;
                overflow-y: auto !important;
            }
            /* Show scrollbars where needed */
            *::-webkit-scrollbar { 
                width: 8px !important; 
                height: 8px !important; 
            }
            * {
                scrollbar-width: thin !important;    /* Firefox */
                -ms-overflow-style: auto !important; /* IE/Edge */
            }
            /* Specifically target Gradio's header container */
            .gradio-container > section > header,
            .gradio-container > section > header > div {
                overflow-x: hidden !important;
            }
            /* Guarantee the Markdown block that renders your "# 🎧 Kokoro Audiobook Generator" also clips */
            .gradio-container .markdown:first-of-type {
                overflow-x: hidden !important;
                white-space: nowrap !important;
                text-overflow: ellipsis !important;
                max-width: 100vw !important;
            }
        """) as interface:
            gr.Markdown("<div style='margin-top: 0px;'></div>")  
            gr.Markdown("# 🎧 Kokoro Audiobook Generator")
            
            with gr.Column(elem_classes=["main-content-column"]):
                with gr.Tabs() as tabs:
                    with gr.TabItem("Settings"):
                        self.create_settings_panel()
                    
                    with gr.TabItem("Raw Text"):
                        with gr.Column(elem_classes=["tab-panel-content-column"]):
                            self.create_raw_text_panel()
                    
                    with gr.TabItem("Sections"):
                        with gr.Column(elem_classes=["tab-panel-content-column"]):
                            self.create_sections_panel()
            
            # Set up event handlers
            self.setup_event_handlers()
        
        return interface
    
    def create_settings_panel(self):
        """Create the settings panel."""
        self.file_input = gr.File(
            label="Upload Text File",
            file_types=[".txt", ".epub", ".pdf"]
        )
        
        gr.Markdown("### Voice Settings")
        self.voice_dropdown = gr.Dropdown(
            choices=self.ui.available_voices,
            value=self.ui.available_voices[0],
            label="Select Voice"
        )
        self.speed_slider = gr.Slider(
            minimum=0.5,
            maximum=2.0,
            value=1.0,
            step=0.1,
            label="Speech Speed"
        )
        
        gr.Markdown("### RVC Settings")
        with gr.Group():
            self.use_rvc = gr.Checkbox(label="Enable RVC Voice Conversion", value=False)
            self.rvc_model = gr.Dropdown(
                choices=self.ui.update_rvc_models(),
                label="RVC Model",
                visible=False
            )
            self.f0_up_key = gr.Slider(
                minimum=-12,
                maximum=12,
                value=0,
                step=1,
                label="Pitch Shift (semitones)",
                visible=False
            )
            self.f0_method = gr.Dropdown(
                choices=["harvest", "crepe", "rmvpe", "pm"],
                value="rmvpe",
                label="Pitch Extraction Method",
                visible=False
            )
            self.index_rate = gr.Slider(
                minimum=0.0,
                maximum=1.0,
                value=1,
                step=0.1,
                label="Index Rate",
                visible=False
            )
            
            # Set RVC control attributes in UI class
            self.ui.rvc_model = self.rvc_model
            self.ui.f0_up_key = self.f0_up_key
            self.ui.f0_method = self.f0_method
            self.ui.index_rate = self.index_rate
        
        gr.Markdown("### Generation Controls")
        with gr.Row():
            self.generate_btn = gr.Button("Generate Audio", variant="primary")
            self.stop_btn = gr.Button("Pause Generation", variant="stop")
            self.continue_btn = gr.Button("Continue Generation", variant="secondary")
        
        with gr.Accordion("Regeneration Controls", open=False):
            with gr.Column():
                with gr.Row():
                    self.section_number = gr.Number(
                        label="Section Number",
                        precision=0
                    )
                with gr.Row():
                    self.regenerate_section_btn = gr.Button("Regenerate This Section", variant="secondary")
                    self.regenerate_from_btn = gr.Button("Regenerate From This Section", variant="secondary")
        
        # Audio Player Section
        with gr.Accordion("Audio Player", open=False):
            self.track_selector = gr.Dropdown(
                label="Now Playing",
                choices=["No sections available"],
                value="No sections available",
                interactive=True,
                allow_custom_value=True,
                type="value"
            )
            self.audio_player = gr.Audio(label="Audio Player", interactive=False, autoplay=False)
            with gr.Row():
                self.prev_btn = gr.Button("⏮ Previous", variant="secondary")
                self.next_btn = gr.Button("Next ⏭", variant="secondary")
        
        # Download Complete Audiobook Section
        with gr.Accordion("Download Complete Audiobook", open=False):
            with gr.Column():
                with gr.Row():
                    self.concatenate_btn = gr.Button("Concatenate Audio Files", variant="primary")
                with gr.Row():
                    self.download_btn = gr.File(label="Download Complete Audiobook", visible=False)
                self.download_status = gr.Textbox(label="Download Status", visible=False)
                
                # Set download components in UI class
                self.ui.download_btn = self.download_btn
                self.ui.download_status = self.download_status
        
        # Status bar at the bottom
        self.generate_status = gr.Textbox(label="Status")
        self.ui.generate_status = self.generate_status
    
    def create_sections_panel(self):
        """Create the sections panel."""
        with gr.Column(elem_classes=["sections-container"]):
            self.sections_list = gr.Dataframe(
                headers=["Section", "Content"],
                datatype=["str", "str"],
                col_count=(2, "fixed"),
                row_count=(1, "dynamic"),
                value=[["", ""]],
                visible=False
            )
            self.ui.sections_list = self.sections_list
    
    def create_raw_text_panel(self):
        """Create the raw text panel."""
        with gr.Column(elem_classes=["raw-text-container"]):
            self.raw_text = gr.Textbox(
                label="Raw Text",
                placeholder="Enter or paste your text here...",
                lines=20,
                elem_classes=["raw-text-panel-content"]
            )
            self.update_sections_btn = gr.Button("Update Sections", variant="primary")
    
    def setup_event_handlers(self):
        """Set up event handlers for UI components."""
        # File upload handler
        self.file_input.upload(
            fn=self.ui.handlers.handle_file_upload,
            inputs=[self.file_input],
            outputs=[self.sections_list, self.track_selector, self.audio_player, self.raw_text]
        )
        
        # Raw text processing handler
        self.raw_text.change(
            fn=self.ui.handlers.handle_raw_text_processing,
            inputs=[self.raw_text],
            outputs=[self.sections_list]
        )
        
        # Update sections button handler
        self.update_sections_btn.click(
            fn=self.ui.handlers.handle_text_update,
            inputs=[self.raw_text],
            outputs=[self.sections_list]
        )
        
        self.use_rvc.change(
            fn=self.ui.handlers.toggle_rvc_controls,
            inputs=[self.use_rvc],
            outputs=[self.rvc_model, self.f0_up_key, self.f0_method, self.index_rate]
        )
        
        self.rvc_model.change(
            fn=self.ui.handlers.update_rvc_models,
            inputs=[],
            outputs=[self.rvc_model]
        )
        
        self.generate_btn.click(
            fn=lambda *args: self.ui.handlers.handle_generation_complete(*self.ui.audio_generator.generate_audio(*args)),
            inputs=[
                self.sections_list,
                self.voice_dropdown,
                self.speed_slider,
                self.use_rvc,
                self.rvc_model,
                self.f0_up_key,
                self.f0_method,
                self.index_rate
            ],
            outputs=[self.audio_player, self.generate_status, self.track_selector]
        )
        
        self.stop_btn.click(
            fn=self.ui.handlers.handle_stop_generation,
            inputs=[],
            outputs=[self.generate_status, self.audio_player, self.track_selector]
        )
        
        self.continue_btn.click(
            fn=lambda *args: self.ui.handlers.handle_generation_complete(*self.ui.audio_generator.continue_generation(*args)),
            inputs=[
                self.sections_list,
                self.voice_dropdown,
                self.speed_slider,
                self.use_rvc,
                self.rvc_model,
                self.f0_up_key,
                self.f0_method,
                self.index_rate
            ],
            outputs=[self.audio_player, self.generate_status, self.track_selector]
        )
        
        self.regenerate_section_btn.click(
            fn=lambda *args: self.ui.handlers.handle_generation_complete(*self.ui.audio_generator.regenerate_section(*args)),
            inputs=[
                self.section_number,
                self.voice_dropdown,
                self.speed_slider,
                self.use_rvc,
                self.rvc_model,
                self.f0_up_key,
                self.f0_method,
                self.index_rate
            ],
            outputs=[self.audio_player, self.generate_status, self.track_selector]
        )
        
        self.regenerate_from_btn.click(
            fn=lambda *args: self.ui.handlers.handle_generation_complete(*self.ui.audio_generator.regenerate_from_section(*args)),
            inputs=[
                self.section_number,
                self.voice_dropdown,
                self.speed_slider,
                self.use_rvc,
                self.rvc_model,
                self.f0_up_key,
                self.f0_method,
                self.index_rate
            ],
            outputs=[self.audio_player, self.generate_status, self.track_selector]
        )
        
        self.next_btn.click(
            fn=self.ui.handlers.handle_next,
            inputs=[],
            outputs=[self.audio_player, self.track_selector]
        )
        
        self.prev_btn.click(
            fn=self.ui.handlers.handle_previous,
            inputs=[],
            outputs=[self.audio_player, self.track_selector]
        )
        
        self.track_selector.change(
            fn=self.ui.handlers.on_track_selected,
            inputs=[self.track_selector],
            outputs=[self.audio_player, self.track_selector]
        )
        
        self.concatenate_btn.click(
            fn=self.ui.handlers.handle_concatenation,
            inputs=[],
            outputs=[self.download_btn, self.download_status]
        ) 