library(shiny)
library(bslib)
library(tidyverse)
library(querychat)
library(plotly)

# ggplot theme
theme_set(theme_minimal())

# Load data
stages <- read_csv(here::here("data", "stages.csv"))

# Querychat config
querychat_config <- querychat_init(
  stages,
  # Configure Databricks Claude as the underlying LLM
  # create_chat_func = purrr::partial(ellmer::chat_databricks(model = "databricks-claude-3-7-sonnet")),
  greeting = readLines(here::here("greeting.md")),
  data_description = readLines(here::here("data_description.md"))
)

ui <- page_sidebar(
  title = tagList(
  img(src = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/Tour_de_France_logo.svg/193px-Tour_de_France_logo.svg.png", 
      height = "30px",
      style = "margin-right: 15px;"),
  "Tour de France Analysis"
),
  sidebar = querychat_sidebar("chat"),
  layout_columns(
    card(
      full_screen = TRUE,
      card_header("Most Stage Wins"),
      plotOutput("stages_won")
    ),
    card(
      full_screen = TRUE,
      card_header("Most Stages Completed"),
      plotOutput("stages_ridden")
    )
  ),
  card(
    full_screen = TRUE,
    card_header("Stage Time Distribution"),
    plotlyOutput("stage_time_distribution_plot")
  ),
  card(
    full_screen = TRUE,
    card_header("Rider Age Distribution"),
    plotlyOutput("age_distribution_plot")
  ),
  card(
    full_screen = TRUE,
    card_header("TdF Attrition"),
    plotlyOutput("attrition_plot")
  )
)

server <- function(input, output, session) {
  # Create querychat object
  querychat <- querychat_server("chat", querychat_config)
  
  output$stages_won <- renderPlot({
    querychat$df() |> 
      filter(rank == 1) |> 
      count(rider, sort = TRUE) |> 
      top_n(5) |> 
      ggplot(aes(x = reorder(rider, n), y = n)) +
      geom_col() +
      geom_text(
        aes(label = n),
        color = "white",
        hjust = 1.2,
        size = 4
      ) +
      labs(x = NULL, y = NULL) +
      theme(axis.ticks.x = element_blank(),
            axis.text.x = element_blank()) +
      coord_flip()
  })

  output$stages_ridden <- renderPlot({
    querychat$df() |> 
      count(rider, sort = TRUE) |> 
      top_n(5) |> 
      ggplot(aes(x = reorder(rider, n), y = n)) +
      geom_col() +
      geom_text(
        aes(label = n),
        color = "white",
        hjust = 1.2,
        size = 4
      ) +
      labs(x = NULL, y = NULL) +
      theme(axis.ticks.x = element_blank(),
            axis.text.x = element_blank()) +
      coord_flip()
  })

  output$stage_time_distribution_plot <- renderPlotly({
    p <- querychat$df() |> 
      filter(!is.na(elapsed)) |>
      # Group by year and stage to identify outliers within each stage
      group_by(year, stage_results_id) |>
      # Remove times that are extreme outliers (beyond 1.5 IQR)
      mutate(
        q1 = quantile(elapsed, 0.25),
        q3 = quantile(elapsed, 0.75),
        iqr = q3 - q1,
        is_outlier = elapsed < (q1 - 1.5 * iqr) | elapsed > (q3 + 1.5 * iqr)
      ) |>
      filter(!is_outlier) |>
      ungroup() |>
      ggplot(aes(x = elapsed, group = year)) +
      geom_density(alpha = 0.5) +
      labs(x = "Stage Time (seconds)",
           y = NULL) +
      theme(axis.text = element_blank(),
            axis.ticks = element_blank())
    
    ggplotly(p)
  })
  
  output$age_distribution_plot <- renderPlotly({
    p <- querychat$df() |> 
      select(rider, age, year) |> 
      filter(!is.na(age)) |> 
      distinct() |> 
      ggplot(aes(x = age, group = year)) +
      geom_density(alpha = 0.5) +
      labs(x = "Rider Age",
           y = NULL) +
      theme(axis.text.y = element_blank(),
      axis.ticks.y = element_blank())
    
    ggplotly(p)
  })
  
  output$attrition_plot <- renderPlotly({
    stage_results_id_lvls <- paste0("stage-", rep(0:22, each = 3), c("", "a", "b"))
    attrition <- querychat$df() |> 
      mutate(stage_results_id = factor(stage_results_id, levels = stage_results_id_lvls)) |>
      group_by(year, stage_results_id) |> 
      summarise(num_finishers = n_distinct(rider)) |> 
      group_by(year) |> 
      mutate(pct_finishers = num_finishers / max(num_finishers)) |> 
      arrange(year, stage_results_id)

    p <- attrition |>
      filter() |> 
      ggplot(aes(x = stage_results_id, y = pct_finishers, group = as.factor(year))) +
      geom_line(alpha = 0.5) +
      labs(x = "Stage", y = NULL) +
      scale_y_continuous(labels = scales::percent) +
      # Remove x axis labels
      theme(axis.text.x = element_blank())
    
    ggplotly(p)
  })
}

  shinyApp(ui, server)